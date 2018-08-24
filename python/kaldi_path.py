#!/usr/bin/python3
"""
USAGE: 
  import kaldi_path
  kaldi_path.set(kaldi_root, srilm_path)
"""
import os

def set(kaldi_root, srilm_path):
    '''USAGE: kaldi_path.set(kaldi_root, srilm_path)
    This feeds os.environ['PATH'] with locations of standard programs.
    It also feeds os.environ['LD_LIBRARY_PATH'] with standard dynamic libraries.
    '''

    os.environ['KALDI_ROOT']=kaldi_root

    # Get the current path, and appent srilm_path
    if 'PATH' in os.environ:
        kaldi_path= os.environ['PATH'].split(':')
    else:
        kaldi_path = []
    kaldi_path.append(srilm_path)
    
    # tools: sph2pipe, and openfst/bin
    kaldi_path += [ os.path.join(kaldi_root,'tools',x) for x in [
        'sph2pipe_v2.5',
        os.path.join('openfst','bin')
    ]]
    
    # kaldi binaries: many, as listed.
    kaldi_path += [ os.path.join(kaldi_root,'src',x) for x in [
        'bin',
        'fstbin',
        'gmmbin',
        'featbin',
        'lm',
        'sgmmbin',
        'sgmm2bin',
        'latbin',
        'nnetbin',
        'nnet2bin',
        'nnet3bin',
        'lmbin',
        'kwsbin'
    ]]
    # current directory, and its utils subdirectory
    kaldi_path += [ os.path.join(os.getcwd(),'utils'), os.getcwd() ]

    # Set the os.environ['PATH']
    os.environ['PATH']=':'.join(kaldi_path)

    # Add tools/openfst/lib to the LD_LIBRARY_PATH
    if 'LD_LIBRARY_PATH' in os.environ:
        ld_library_path= os.environ['LD_LIBRARY_PATH'].split(':')
    else:
        ld_library_path = []
    ld_library_path += [ os.path.join(kaldi_root,'tools','openfst','lib') ]
    os.environ['LD_LIBRARY_PATH'] = ':'.join(ld_library_path)
