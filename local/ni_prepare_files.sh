#!/bin/bash -e

function read_filename () {
  local filename=`expr "X$1" : '[^=]*=\(.*\)'`;
  [ -e "$filename" ] || { echo "Argument '$filename' not a file" >&2; exit 1; }
  echo $filename
}

function read_dirname () {
  local dir_name=`expr "X$1" : '[^=]*=\(.*\)'`;
  [ -d "$dir_name" ] || { echo "Argument '$dir_name' not a directory" >&2; exit 1; }
  local retval=`cd $dir_name 2>/dev/null && pwd || exit 1`
  echo $retval
}

PROG=`basename $0`;
usage="Usage: $PROG <arguments> <LANGUAGE>\n
Prepare train, test file lists for NI ASR.\n\n
Required arguments:\n
  --corpus-dir=DIR\tDirectory for the audio\n
  --list-dir=DIR\tDirectory containing the train/eval split\n
  --trans-file=FILENAME\tFile containing all transcriptions split\n
Creates the files data/LCODE/{train,dev,eval}/{text,wav.scp,utt2spk,spk2utt}\n
Creates the files data/LCODE/wav\n
";

if [ $# -lt 3 ]; then
  echo -e $usage; exit 1;
fi

while [ $# -gt 0 ];
do
  case "$1" in
  --help) echo -e $usage; exit 0 ;;
  --corpus-dir=*) 
  CORPUSDIR=`read_dirname $1`; shift ;;
  --trans-file=*)
  TRANSFILE=`read_filename $1`; shift ;;
  --list-dir=*)
  LISTDIR=`read_dirname $1`; shift ;;
  *) LCODE=$1; shift ;;
  esac
done

[ -f path.sh ] && . path.sh  # Sets the PATH to contain necessary executables

full_name=$LCODE
echo "$0: Checking train.txt and eval.txt in $LISTDIR"
num_train_files=$(wc -l $LISTDIR/train.txt | awk '{print $1}')
num_eval_files=$(wc -l $LISTDIR/eval.txt | awk '{print $1}')

if [[ $num_train_files -eq 0 || $num_eval_files -eq 0 ]]; then
    echo "No utterances found in $LISTDIR/train.txt OR $LISTDIR/eval.txt" && exit 1
fi
# Checking if sox is installed
echo "$0: checking for sox"
which sox > /dev/null

echo "$0: creating a directory for downsampled WAV files"
mkdir -p data/$LCODE/wav # directory storing all the downsampled WAV files
tmpdir=$(mktemp -d);
echo $tmpdir
trap 'rm -rf "$tmpdir"' EXIT
mkdir -p $tmpdir
mkdir -p $tmpdir/downsample
mkdir -p $tmpdir/trans

soxerr=$tmpdir/soxerr;

for x in train dev eval; do
    echo "$0: Downsampling $x"

    file="$LISTDIR/$x.txt"
    mkdir -p data/$LCODE/wav/$x
    >$soxerr
    nsoxerr=0
    while read line; do
        set +e
        base=`basename $line .wav`
        wavfile="$CORPUSDIR/$base.wav"
        outwavfile="data/$LCODE/wav/$x/$base.wav"
        [[ -e $outwavfile ]] || sox $wavfile -R -r 8000 -t wav $outwavfile
        if [ $? -ne 0 ]; then
            echo "$wavfile: exit status = $?" >> $soxerr
            let "nsoxerr+=1"
        else 
            nsamples=`soxi -s "$outwavfile"`;
            if [[ "$nsamples" -gt 1000 ]]; then
                echo "$outwavfile" >> $tmpdir/downsample/${x}_wav
            else
                echo "$outwavfile: #samples = $nsamples" >> $soxerr;
                let "nsoxerr+=1"
            fi
        fi
        set -e
    done < "$file"

    [[ "$nsoxerr" -gt 0 ]] && echo "sox: error converting following $nsoxerr file(s):" >&2
    [ -f "$soxerr" ] && cat "$soxerr" >&2

    echo "$0: Prepare ${x}_wav.scp"
    sed -e "s:.*/::" -e 's:.wav$::' $tmpdir/downsample/${x}_wav > $tmpdir/downsample/${x}_basenames_wav
    paste $tmpdir/downsample/${x}_basenames_wav $tmpdir/downsample/${x}_wav | sort -k1,1 > data/${LCODE}/$x/wav.scp

    echo "$0: Prepare ${x}_utt2spk and ${x}_spk2utt"
    sed -e 's:\-.*$::' $tmpdir/downsample/${x}_basenames_wav | \
        paste -d' ' $tmpdir/downsample/${x}_basenames_wav - | sort -t' ' -k1,1 \
        > data/${LCODE}/$x/utt2spk

    ./utils/utt2spk_to_spk2utt.pl data/${LCODE}/$x/utt2spk >  data/${LCODE}/$x/spk2utt || exit 1;

    echo "$0: preparing ${x}_text"
    ( for i in `cat $LISTDIR/${x}.txt | sed 's/\.wav//g'`; do
	  LC_ALL=en_US.UTF-8 grep $i $TRANSFILE;
	  done )  | LC_ALL=en_US.UTF-8 sort -k1,1 > data/${LCODE}/$x/text
done

