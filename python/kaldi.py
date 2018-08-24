#!/usr/bin/python3
"""
USAGE: 
  import kaldi
  kaldi.set_path(kaldi_root, srilm_path)
  Use other utils as useful.
"""
import os,sys
import subprocess

def set_path(kaldi_root, srilm_path):
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

class CMD:
    '''Class that contains optimization information such as nproc, train_cmd, and decode_cmd'''
    def __init__(self, nproc, train_cmd, decode_cmd):
        self.nproc = nproc
        self.train_cmd = train_cmd
        self.decode_cmd = decode_cmd

def newer_than(file1,file2):
    if not os.path.exists(file2):
        return(True)
    if os.path.getmtime(file1) > os.path.getmtime(file1):
        return(True)
    else:
        return(False)
def read_dict_from_file(filename):
    '''Read a dictionary from a file.  First word on each line is the key, remainder is the entry.'''
    dict = {}
    with open(filename) as f:
        for line in f:
            words = line.rstrip().split()
            dict[words[0]] = ' '.join(words[1:])
    return(dict)
def read_list_from_file(filename):
    '''Read a list of words from a file.  Doesn't matter if they're separated by spaces or newlines'''
    with open(filename) as f:
        result = f.read().split()
    return(result)
def write_dict_to_file(d, filename):
    '''Write a dictionary to a file: first word on each line is the key, remainder are the entry.'''
    with open(filename,"w") as f:
        for (k,v) in sorted(d.items()):
            f.write('{}\t{}\n'.format(k,v))
def write_list_to_file(data, filename, separator):
    '''Write a list to a file, with separator between list items'''
    with open(filename,'w') as f:
        f.write(separator.join(data)+'\n')

def convert_if_newer(ifile, ofile, cmd, stdout_logfile, stderr_logfile):
    '''Create ofile from ifile if ifile is newer.  Pipe errors to logfiles; return the returncode.
    USAGE:
    ifile: string, input filename
    ofile: string, output filename
    cmd: list of words for the subprocess run
    stdout_logfile: open file object
    stderr_logfile: open file object
    '''
    stdout_logfile.write(' '.join(cmd)+'\n')
    stderr_logfile.write(' '.join(cmd)+'\n')
    if newer_than(ifile, ofile):
        try:
            c = subprocess.run(cmd,stdout=stdout_logfile,stderr=stderr_logfile)
            return(c.returncode)
        except subprocess.CalledProcessError as err:
            stdout_logfile.write(err.stdout)
            stderr_logfile.write(err.stdout)
            return(err.returncode)
    else:
        return(0)    
    
