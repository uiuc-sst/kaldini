#!/usr/bin/python3
"""
  import SpeechCorpus
  c1 = SpeechCorpus.corpus(utt2wav, utt2spk, utt2txt)
  Useful methods:
   c1.downsample
   c1.write_dicts_to_dictfiles
   c1.make_mfcc
   c1.compute_cmvn_stats
"""

import os
import subprocess
import re
import shutil
import kaldi

########## auxilary functions ##################################################
def get_utt_from_filename(ifile):
    '''Compute a standardized utterance ID from a full waveform filename.'''
    (wavhead, wavtail) = os.path.split(ifile)
    (wavroot, wavext) = os.path.splitext(wavtail)
    return(wavroot)
def get_spk_from_utt(utt):
    '''Standard speaker ID: remove all characters from the first dash (-) rightward'''
    spk = re.sub(r'-.*','', utt)
    return(spk)
        
########## corpus object ##################################################
class corpus:
    '''This class defines a speech corpus'''
    def __init__(self, utt2wav, utt2spk, utt2txt):
        '''USAGE: corpus=SpeechCorpus(utt2wav, utt2spk, utt2txt)
        utt2wav: a dictionary mapping from utt_id to filename, or the name of a file containing such.
        utt2spk: a dictionary mapping from utt_id to spk_id, or the name of a file containing such.
        utt2txt: a dictionary mapping from utt_id to text, or the name of a file containing such.
        '''
        self.utt2spk = utt2spk
        self.utt2txt = utt2txt
        self.utt2wav = utt2wav
        # Make sure that the waveform files exist; if not, throw an error!
        u2w = kaldi.read_dict_from_file(utt2wav) if isinstance(utt2wav, str) else utt2wav
        for (u,w) in u2w.items():
            x = re.sub(r':.*','',w)  # Eliminate the index-into-file part, to test file existence
            if not os.path.exists(x):
                raise FileNotFoundError('SpeechCorpus: {} -> {}, but file {} not found'.format(u,w,x))
        
    def downsample(self, fs, logdir, wavdir):
        '''USAGE: other = self.downsample(fs, logdir, wavdir)
        fs = output sampling rate
        logdir = directory for logfiles describing downsampling errors
        wavdir = downsampled files will go into wavdir
        '''
        utt2wav = kaldi.read_dict_from_file(self.utt2wav) if isinstance(self.utt2wav, str) else self.utt2wav
        soxerr = []
        valid_wavs = {}
        os.makedirs(wavdir,exist_ok=True)
        os.makedirs(logdir,exist_ok=True)
        with open(os.path.join(logdir,'sox_stderr.txt'),'w') as sox_stderr:
            with open(os.path.join(logdir,'sox_stdout.txt'),'w') as sox_stdout:                
                for (utt, ifile) in utt2wav.items():
                    (wavhead, wavtail) = os.path.split(ifile)
                    (wavroot, wavext) = os.path.splitext(wavtail)
                    ofile = os.path.join(wavdir,wavroot+'.wav')
                    cmd = ['sox',ifile,'-R','-r',str(fs),'-t','wav',ofile]
                    returncode = kaldi.convert_if_newer(ifile, ofile, cmd, sox_stdout, sox_stderr)
                    if returncode==0:
                        valid_wavs[utt]=ofile
        other = corpus(utt2wav = valid_wavs, utt2spk=self.utt2spk, utt2txt=self.utt2txt)
        return(other)
    
    def write_dicts_to_dictfiles(self, utt2wav, utt2spk, spk2utt, utt2txt):
        '''USAGE: other=self.write_dicts_to_dictfiles(utt2wav, utt2spk, spk2utt, utt2txt)
        This creates a new SpeechCorpus in which self.utt2wav, self.utt2spk, and self.utt2txt
        have been written to the files named utt2wav, utt2spk, and utt2txt,
        and a corresponding file spk2utt has also been created.
        Utterance IDs in every output dictionary are limited to the set intersection of the 
        inputs.
        '''
        u2w = kaldi.read_dict_from_file(self.utt2wav) if isinstance(self.utt2wav, str) else self.utt2wav
        u2s = kaldi.read_dict_from_file(self.utt2spk) if isinstance(self.utt2spk, str) else self.utt2spk
        u2t = kaldi.read_dict_from_file(self.utt2txt) if isinstance(self.utt2txt, str) else self.utt2txt 
        common_keys = sorted(list(set.intersection(set(u2w.keys()), set(u2s.keys()), set(u2t.keys()))))
        kaldi.write_dict_to_file({ k:u2w[k] for k in common_keys }, utt2wav)
        kaldi.write_dict_to_file({ k:u2s[k] for k in common_keys }, utt2spk)
        kaldi.write_dict_to_file({ k:u2t[k] for k in common_keys }, utt2txt)
        s2u = {s:' '.join([u for u in common_keys if u2s[u]==s]) for s in set(self.utt2spk.values())}
        kaldi.write_dict_to_file(s2u, spk2utt)
        # Create a new corpus with filenames instead of dicts, and return it
        return(corpus(utt2wav=utt2wav, utt2spk=utt2spk, utt2txt=utt2txt))
        
    def make_mfcc(self, kaldi_cmd, logdir, mfccdir):
        '''USAGE: other=self.make_mfcc(kaldi_cmd, logdir, mfccdir)
        Create MFCCs in mfccdir, put logs in logdir, if the feature files do not already exist.
        self.utt2wav must be a wav.scp filename.
        other.utt2wav is set to the corresponding feats.scp filename.
        '''
        (datadir, wav_scp) = os.path.split(self.utt2wav)
        utt2wav = kaldi.read_dict_from_file(self.utt2wav)

        if not os.path.isabs(mfccdir):
            mfccdir = os.path.join(os.getcwd(),mfccdir)
        os.makedirs(mfccdir, exist_ok=True)
        os.makedirs(logdir, exist_ok=True)

        # use "name" as part of name of the archive.
        name=os.path.basename(datadir)

        # Check if feats.scp already exists.
        # If so, load it as a dictionary, so we can compare its mtimes to wav.scp files
        utt2feat_file = os.path.join(datadir,'feats.scp')
        utt2feat = {}
        if os.path.exists(utt2feat_file):
            utt2feat = kaldi.read_dict_from_file(utt2feat_file)
            # If utt2feat has 95% of the keys of utt2wav, and its files are all newer, then return
            missing_utts = list(set(utt2wav.keys())-set(utt2feat.keys()))
            if len(missing_utts) < 0.05*len(utt2wav):
                wt = max([ os.path.getmtime(w) for w in utt2wav.values() ])
                ft = min([ os.path.getmtime(re.sub(r':.*','',f)) for f in utt2feat.values() ])
                print('Max wav time is {}, min feat time is {}'.format(wt,ft))
                if ft > wt:
                    print(__name__+': doing nothing because mfcc newer than wavs in '+datadir)
                    return(other)
            else:
                print('Utts not in feat: {}, including {}'.format(len(missing_utts),missing_utts[0]))
    
            os.makedirs(os.path.join(datadir,'.backup'),exist_ok=True)
            print("make_mfcc: moving feats.scp to {}/.backup".format(datadir))
            shutil.move(utt2feat_file,os.path.join(datadir,'.backup','feats.scp'))

        mfcc_config = os.path.join(os.getcwd(), 'conf', 'mfcc.conf')
        if not os.path.exists(mfcc_config):
            raise FileNotFoundError('SpeechCorpus.corpus.make_mfcc requires '+mfcc_config)

        print(__name__+": [info]: this function assumes wav.scp indexed by utterance, not segments")
        split_scps=[ os.path.join(logdir,'wav_{}.{}.scp'.format(name,n)) for n in range(1,kaldi_cmd.nproc+1) ]
        scp_lines = [ '%s %s\n' % (k,v) for (k,v) in utt2wav.items() ]
        num_per_job = float(len(scp_lines))/kaldi_cmd.nproc
        for n in range(0,kaldi_cmd.nproc):
            with open(split_scps[n],'w') as f:
                f.writelines(scp_lines[int(n*num_per_job):int((n+1)*num_per_job)])

        # This is done using run.pl to parallelize, just to make other queue managers easier
        cmd = [ kaldi_cmd.train_cmd, 'JOB=1:%d'%(kaldi_cmd.nproc), os.path.join(logdir,'make_mfcc_%s.JOB.log'%name),
                'compute-mfcc-feats',  '--verbose=2', '--config=%s'%mfcc_config, 
                'scp,p:%s/wav_%s.JOB.scp'%(logdir,name), 'ark:-', '|',
                'copy-feats', '--compress=true', 'ark:-',
                'ark,scp:%s/raw_mfcc_%s.JOB.ark,%s/raw_mfcc_%s.JOB.scp'%(mfccdir,name,mfccdir,name)
        ]
        subprocess.run(cmd)

        assert (not os.path.exists(os.path.join(logdir,'.error.'+name))),'%s: Error producing mfcc features for %s, see %s/make_mfcc_%s.1.log'%(__name__,name,logdir,name)

        utt2feat = {}
        for n in range(1,kaldi_cmd.nproc):
            utt2feat.update(kaldi.read_dict_from_file(os.path.join(mfccdir,'raw_mfcc_%s.%d.scp'%(name,n))))
        kaldi.write_dict_to_file(utt2feat, utt2feat_file)

        for f in split_scps:
            os.remove(f)

        if len(utt2feat)!=len(utt2wav):
            print("Not all feature files successfully processed (%d<%d);"%(len(utt2feat),len(utt2wav)))
            print("Calling utils/fix_data_dir.sh %s" % datadir)
            cmd = ['utils/fix_data_dir.sh',datadir]
            subprocess.run(cmd)
        if len(utt2feat) < int(0.95*len(utt2wav)):
            print("Less than 95\% the features were successfully generated.  Probably a serious error.")
        print("Succeeded creating MFCC features for %s" % name)
        return(corpus(utt2wav=utt2feat_file, utt2spk=self.utt2spk, utt2txt=self.utt2txt))
                
    def compute_cmvn_stats(self, logdir, mfccdir):
        '''USAGE: self.compute_cmvn_stats(logdir, mfccdir)
        Compute cepstral mean and variance normalization stats for the MFCCs in mfcdir.
        self.utt2wav, self.utt2spk must be files in the same directory.
        '''
        (datadir, wav_scp) = os.path.split(self.utt2wav)
        cmd=['steps/compute_cmvn_stats.sh',datadir,logdir,mfccdir]
        subprocess.run(cmd)
        
    def datadir(self):
        '''USAGE datadir=SpeechCorpus.corpus.datadir()
        Returns the directory in which the file utt2spk resides.
        Throws an error if utt2spk is not a string.
        '''
        if isinstance(self.utt2spk,str):
            (datadir,filename) = os.path.split(self.utt2spk)
            return(datadir)
        else:
            raise TypeError(__name__+': self.utt2spk should be str, not {}'.format(self.utt2spk))
    
