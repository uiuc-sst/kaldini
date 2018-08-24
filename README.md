## Usage:
```
git clone https://www.github.com/kaldi-asr/kaldi
mkdir kaldi/egs
git clone https://www.github.com/uiuc-sst/kaldini
cd kaldini
```

The goals of this project:

1. Train and test an ASR from scratch using the kind of data that you can get from
a small group of native informants in a new language in about five hours of contact 
time, i.e., only about 1000 read sentences.

2. Explore the use of python to train and test kaldi recognizers, bypassing some of 
Dan Povey's heavily tested but obscure bash scripts.  Sometimes my python scripts
call his bash scripts, just because often that's the most efficient way to make it
work.  This is all really experimental.

Anyway, the python code is in the python subdirectory.  The script run.sh still
points to bash versions of the same thing.  I don't remember which ones run and 
which ones don't, right now.
