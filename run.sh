#!/bin/bash -e
# run_monophone.sh: 
# Train a monophone ASR from a small amount of incident language data recorded by a native informant.
# Currently uses only monophone training, since that gave lowest WER for Tamil.
# Other parts tested for Tamil are in run_triphone.sh.
# Mark Hasegawa-Johnson, 6/2018
# Adapted from ws15code/SBS-mul


[ -f cmd.sh ] && source ./cmd.sh \
  || echo "cmd.sh not found. Jobs may not execute properly."

. path.sh || { echo "Cannot source path.sh"; exit 1; }

# Language ID
L=tam
CORPUS_ROOT=/Users/jhasegaw/data/2018march/${L}

# $NI_CORPUS contains all audio files: train, dev, and eval
NI_CORPUS=${CORPUS_ROOT}/ni/01/audio/
# $NI_TRANSCRIPTS contains {train,dev}.txt transcription files
NI_TRANSCRIPTS=${CORPUS_ROOT}/ni/01/labels/labels.txt
# $NI_LISTDIR contains {train,dev,eval}.txt files, containing filenames, one per line
NI_LISTDIR=${CORPUS_ROOT}/ni/01/lists/
# $IL_{LEXICON,LM,WORDLIST,PHONELIST} should be as provided by mkprondict2.py and by Gina
IL_LEXICON=${CORPUS_ROOT}/mark/tamil_prondict_ref.txt
IL_LM=${CORPUS_ROOT}/mark/lm.arpa
IL_WORDLIST=${CORPUS_ROOT}/mark/words.txt
IL_PHONELIST=${CORPUS_ROOT}/mark/phones.txt

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

# copy and gzip the ARPA LM
echo "$0: cp lm.arpa"
cp $IL_LM data/$L/lang/lm.arpa || exit 1
gzip -f data/$L/lang/lm.arpa
cp $IL_WORDLIST data/$L/dict/words.txt
# create the G.fst
echo "$0: format_lm"
utils/format_lm.sh data/$L/lang data/$L/lang/lm.arpa.gz data/$L/dict/lexicon.txt data/$L/lang || exit 1

echo "$0: MFCC prep"
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

# Find scoring options for the eval scoring.  Best 
# for x in exp/$L/*/decode*; do [ -d $x ] && grep WER $x/wer_* | utils/best_wer.sh; done
scoring_opts=`grep WER exp/$L/mono/decode_dev_$L/wer_* | utils/best_wer.sh | tee exp/$L/mono/decode_dev_$L/best_wer.log | perl -e '$_=<STDIN>;$pat=qw{wer_(\d+)_([\d\.]+)}; if(/$pat/){print("\"--word_ins_penalty $2 --min_lmwt $1 --max_lmwt $1\"\n")}'`

# Eval scoring: use only the wip and lmwt that were best in the dev set
steps/decode.sh --scoring_opts "\"$scoring_opts\"" --nj 4 --cmd "$decode_cmd" $graph_dir data/$L/eval exp/$L/mono/decode_eval_$L &
wait

cp exp/$L/mono/decode_eval_$L/scoring_kaldi/pen*/*.txt exp/$L/mono/decode_eval_$L/transcription_result.txt


