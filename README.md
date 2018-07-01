# kaldini

Usage:
```
git clone https://www.github.com/kaldi-asr/kaldi
mkdir kaldi/egs/kaldini
cd kaldi/egs/kaldini
git clone https://www.github.com/uiuc-sst/kaldini
ln -s ../wsj/s5/steps steps
ln -s ../wsj/s5/utils utils
```

Then you need to edit run.sh in order to point to the language and source directories for the
native informant and incident language input files, then type ```./run.sh```.
