export KALDI_ROOT=$(cd ../.. && pwd)
export SRILM_PATH=/Users/jhasegaw/Dropbox/packages/srilm/bin/macosx
export PATH=${PATH}:$PWD/utils/:$KALDI_ROOT/tools/sph2pipe_v2.5/:$KALDI_ROOT/src/bin:$KALDI_ROOT/tools/openfst/bin:$KALDI_ROOT/tools/irstlm/bin/:$KALDI_ROOT/src/fstbin/:$KALDI_ROOT/src/gmmbin/:$KALDI_ROOT/src/featbin/:$KALDI_ROOT/src/lm/:$KALDI_ROOT/src/sgmmbin/:$KALDI_ROOT/src/sgmm2bin/:$KALDI_ROOT/src/fgmmbin/:$KALDI_ROOT/src/latbin/:$KALDI_ROOT/src/nnetbin:$KALDI_ROOT/src/nnet2bin/:$KALDI_ROOT/src/lmbin/:$KALDI_ROOT/src/kwsbin:$PWD:$SRILM_PATH
export LC_ALL=C
export LD_LIBRARY_PATH=$KALDI_ROOT/tools/openfst/lib
