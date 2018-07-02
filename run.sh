#!/bin/bash -e

# Train a monophone ASR from a small amount of incident language data recorded by a native informant.
# Currently uses only monophone training, because that gave lowest WER for Tamil.
# Other parts tested for Tamil are in ./run_triphones.sh.
# Mark Hasegawa-Johnson, 6/2018
# Adapted from https://github.com/ws15code/SBS-mul.

# Language ID
#L=tam # Tamil
#CORPUS_ROOT=/Users/jhasegaw/data/2018march/$L

# Audio files: train, dev, and eval.
#NI_CORPUS=${CORPUS_ROOT}/ni/01/audio/

# Transcriptions: train.txt, dev.txt.
#NI_TRANSCRIPTS=${CORPUS_ROOT}/ni/01/labels/labels.txt

# {train,dev,eval}.txt, each containing one filename per line.
#NI_LISTDIR=${CORPUS_ROOT}/ni/01/lists/

# These come from mkprondict2.py and Gina.
#IL_LEXICON=${CORPUS_ROOT}/mark/tamil_prondict_ref.txt
#IL_LM=${CORPUS_ROOT}/mark/lm.arpa
#IL_WORDLIST=${CORPUS_ROOT}/mark/words.txt
#IL_PHONELIST=${CORPUS_ROOT}/mark/phones.txt

# Language ID
L=swh # Swahili
CORPUS_ROOT=/Users/jhasegaw/data/2018jun/$L

# Audio files: train, dev, and eval.
NI_CORPUS=${CORPUS_ROOT}/all/audio/

# Transcriptions: train.txt, dev.txt.
NI_TRANSCRIPTS=${CORPUS_ROOT}/all/transcription.txt

# {train,dev,eval}.txt, each containing one filename per line.
NI_LISTDIR=${CORPUS_ROOT}/all/list/

# These come from mkprondict2.py and Gina.
IL_LEXICON=${CORPUS_ROOT}/local/dict/lexicon.txt
IL_LM=${CORPUS_ROOT}/lm.arpa.gina
IL_WORDLIST=${CORPUS_ROOT}/local/dict/words.txt
IL_PHONELIST=${CORPUS_ROOT}/phones.txt

NUMLEAVES=1200
NUMGAUSSIANS=8000
nproc=56

[ -f cmd.sh ] && . ./cmd.sh || echo "cmd.sh not found. Jobs may not execute properly."

. path.sh || { echo "Cannot source path.sh"; exit 1; }

# Get file lists (for audio, transcription, etc.) for the language $L.
echo "$0: preparing data..."
for x in train dev eval; do
    mkdir -p data/$L/$x
done

# Create data/LCODE/{train,dev,eval}/{text,wav.scp,utt2spk,spk2utt} and data/LCODE/wav.
./local/ni_prepare_files.sh --corpus-dir=$NI_CORPUS --list-dir=$NI_LISTDIR \
			    --trans-file=$NI_TRANSCRIPTS $L 
echo "Done." 

echo "$0: language $L: Creating phonesets and clustering questions..."
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
 
echo "$0: lang prep"
utils/prepare_lang.sh --position-dependent-phones false data/$L/dict "<unk>" data/$L/local/lang_tmp data/$L/lang || exit 1

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
mkdir -p $mfccdir
for x in train dev eval; do
    (
    steps/make_mfcc.sh --nj $nproc --cmd "$train_cmd" data/$L/$x exp/$L/make_mfcc/$x $mfccdir
	steps/compute_cmvn_stats.sh data/$L/$x exp/$L/make_mfcc/$x $mfccdir
    ) &
done
wait

# Monophone training.
mkdir -p exp/$L/mono;
steps/train_mono.sh --nj $nproc --cmd "$train_cmd" data/$L/train data/$L/lang exp/$L/mono || exit 1

graph_dir=exp/$L/mono/graph
mkdir -p $graph_dir
utils/mkgraph.sh data/$L/lang exp/$L/mono $graph_dir || exit 1

steps/decode.sh --nj $nproc --cmd "$decode_cmd" $graph_dir data/$L/dev exp/$L/mono/decode_dev_$L &
wait

# Find scoring options for the eval scoring.  Best 
# for x in exp/$L/*/decode*; do [ -d $x ] && grep WER $x/wer_* | utils/best_wer.sh; done
scoring_opts=`grep WER exp/$L/mono/decode_dev_$L/wer_* | utils/best_wer.sh | tee exp/$L/mono/decode_dev_$L/best_wer.log |
  perl -e '$_=<STDIN>;$pat=qw{wer_(\d+)_([\d\.]+)}; if(/$pat/){print("\"--word_ins_penalty $2 --min_lmwt $1 --max_lmwt $1\"\n")}'`

# Eval scoring: use only the wip and lmwt that were best in the dev set
steps/decode.sh --scoring_opts "\"$scoring_opts\"" --nj $nproc --cmd "$decode_cmd" $graph_dir data/$L/eval exp/$L/mono/decode_eval_$L &
wait

cp exp/$L/mono/decode_eval_$L/scoring_kaldi/pen*/*.txt exp/$L/mono/decode_eval_$L/transcription_result.txt
