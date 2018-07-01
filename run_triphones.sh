#!/bin/bash -e
# Train an ASR from a small amount of incident language data recorded by a native informant.
# Mark Hasegawa-Johnson, 6/2018
# Adapted from ws15code/SBS-mul

[ -f cmd.sh ] && source ./cmd.sh \
  || echo "cmd.sh not found. Jobs may not execute properly."

. path.sh || { echo "Cannot source path.sh"; exit 1; }

# Set the location of the NI speech 
NI_CORPUS=/Users/jhasegaw/data/2018march/tam/ni/01/audio/
NI_TRANSCRIPTS=/Users/jhasegaw/data/2018march/tam/ni/01/labels/labels.txt
NI_LISTDIR=/Users/jhasegaw/data/2018march/tam/ni/01/lists/
IL_LEXICON=/Users/jhasegaw/data/2018march/Tamil/mark/tamil_prondict_ref.txt
IL_LM=/Users/jhasegaw/data/2018march/Tamil/mark/lm.arpa
IL_WORDLIST=/Users/jhasegaw/data/2018march/Tamil/mark/words.txt
IL_PHONELIST=/Users/jhasegaw/data/2018march/Tamil/mark/phones.txt
L=tam
NUMLEAVES=1200
NUMGAUSSIANS=8000

# Get the various file lists (for audio, transccritpion etc.) for the specific SBS language
echo "Preparing data..."
for x in train dev eval; do
    mkdir -p data/$L/$x
done
#ni_prepare_files.sh Creates the files data/LCODE/{train,dev,eval}/{text,wav.scp,utt2spk,spk2utt}
#and  data/LCODE/wav
./local/ni_prepare_files.sh --corpus-dir=$NI_CORPUS --list-dir=$NI_LISTDIR \
			    --trans-file=$NI_TRANSCRIPTS $L 
echo "Done." 

echo "Language $L: Creating phonesets and clustering questions..."
mkdir -p data/$L/dict
echo "sil laughter noise oov" > data/$L/dict/extra_questions.txt
echo "sil" > data/$L/dict/optional_silence.txt
cat << EOF > data/$L/dict/silence_phones.txt
sil 
laughter
noise	
oov
EOF
# List all phones in the dictionary
cp $IL_PHONELIST data/$L/dict/nonsilence_phones.txt
cat data/$L/dict/silence_phones.txt data/$L/dict/nonsilence_phones.txt > data/$L/dict/phones.txt
# Copy the dictionary
cp $IL_LEXICON data/$L/dict/lexicon.txt
echo "<unk> oov" >> data/$L/dict/lexicon.txt
if [ data/$L/dict/lexiconp.txt -ot $IL_LEXICON ]; then
    rm -f data/$L/dict/lexiconp.txt
fi
echo "Done."
 
echo "lang prep: $L"
utils/prepare_lang.sh --position-dependent-phones false data/$L/dict "<unk>" data/$L/local/lang_tmp data/$L/lang

echo "LM prep: $L"
# remove file identifiers 
cp $IL_WORDLIST data/$L/dict/words.txt
# copy and gzip the ARPA LM
echo "$0: cp lm.arpa"
cp $IL_LM data/$L/lang/lm.arpa || exit 1
gzip -f data/$L/lang/lm.arpa
# create the G.fst
echo "$0: format_lm"
utils/format_lm.sh data/$L/lang data/$L/lang/lm.arpa.gz data/$L/dict/lexicon.txt data/$L/lang || exit 1

echo "MFCC prep"
mfccdir=mfcc/$L
for x in train dev eval; do
    (
	steps/make_mfcc.sh --nj 4 --cmd "$train_cmd" data/$L/$x exp/$L/make_mfcc/$x $mfccdir
	steps/compute_cmvn_stats.sh data/$L/$x exp/$L/make_mfcc/$x $mfccdir
    ) &
done
wait

mkdir -p exp/$L/mono;
steps/train_mono.sh --nj 8 --cmd "$train_cmd" data/$L/train data/$L/lang exp/$L/mono

graph_dir=exp/$L/mono/graph
mkdir -p $graph_dir

utils/mkgraph.sh data/$L/lang exp/$L/mono $graph_dir

steps/decode.sh --nj 4 --cmd "$decode_cmd" $graph_dir data/$L/dev exp/$L/mono/decode_dev_$L &
wait

# Training/decoding triphone models
mkdir -p exp/$L/mono_ali
steps/align_si.sh --nj 8 --cmd "$train_cmd" data/$L/train data/$L/lang exp/$L/mono exp/$L/mono_ali

# Training triphone models with MFCC+deltas+double-deltas
mkdir -p exp/$L/tri1
steps/train_deltas.sh --boost-silence 1.25 --cmd "$train_cmd" $NUMLEAVES $NUMGAUSSIANS \
  data/$L/train data/$L/lang exp/$L/mono_ali exp/$L/tri1

graph_dir=exp/$L/tri1/graph
mkdir -p $graph_dir

utils/mkgraph.sh data/$L/lang exp/$L/tri1 $graph_dir

steps/decode.sh --nj 4 --cmd "$decode_cmd" $graph_dir data/$L/dev exp/$L/tri1/decode_dev_$L &
wait

mkdir -p exp/tri1_ali
steps/align_si.sh --nj 8 --cmd "$train_cmd" data/$L/train data/$L/lang exp/$L/tri1 exp/$L/tri1_ali

mkdir -p exp/tri2b
steps/train_lda_mllt.sh --cmd "$train_cmd" \
  --splice-opts "--left-context=3 --right-context=3" $NUMLEAVES $NUMGAUSSIANS \
  data/$L/train data/$L/lang exp/$L/tri1_ali exp/$L/tri2b

# Train with LDA+MLLT transforms
graph_dir=exp/$L/tri2b/graph
mkdir -p $graph_dir

utils/mkgraph.sh data/$L/lang exp/$L/tri2b $graph_dir

steps/decode.sh --nj 4 --cmd "$decode_cmd" $graph_dir data/$L/dev exp/$L/tri2b/decode_dev_$L &
wait

mkdir -p exp/$L/tri2b_ali
steps/align_si.sh --nj 8 --cmd "$train_cmd" --use-graphs true \
		  data/$L/train data/$L/lang exp/$L/tri2b exp/$L/tri2b_ali

steps/train_sat.sh --cmd "$train_cmd" $NUMLEAVES $NUMGAUSSIANS \
  data/$L/train data/$L/lang exp/$L/tri2b_ali exp/$L/tri3b

graph_dir=exp/tri3b/graph
mkdir -p $graph_dir
utils/mkgraph.sh data/$L/lang exp/$L/tri3b $graph_dir

steps/decode_fmllr.sh --nj 4 --cmd "$decode_cmd" $graph_dir data/$L/dev \
		      exp/$L/tri3b/decode_dev &
wait

# Getting WER numbers
for x in exp/$L/*/decode*; do [ -d $x ] && grep WER $x/wer_* | utils/best_wer.sh; done
