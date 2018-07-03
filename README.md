## Usage:
```
git clone https://www.github.com/kaldi-asr/kaldi
cd kaldi/tools; make -j $(nproc)
cd ../src;      ./configure --shared && make depend -j $(nproc) && make -j $(nproc)
cd ..;          mkdir egs
git clone https://www.github.com/uiuc-sst/kaldini
cd kaldini
```

Change the variables at the top of run.sh to point to the language and source directories
of the native informant and incident language input files.

`./run.sh`
