#!/usr/bin/python3
"""
USAGE: python HCLG.py language
  If called from the command line, this creates an HCLG object with specified language and corpus,
  accessing Kaldi from the specified kaldi_root and SRILM from the specified path,
  then trains and tests it with default settings from those directories.
  [language] = experimental results will be stored in exp/[language]/... and data/[language]/...
  [corpus] = directory containing the subdirectories audio and list, and the file transcription.txt.
  [kaldi_root] = directory containing the subdirectories tools and src.
  [srilm_path] = directory containing the binary executable file ngram-count.
"""

import os,sys
import subprocess
import shutil
import SpeechCorpus
import kaldi

########## H fst ##################################################
class Hfst:
    '''This class defines an H FST (a set of triphone or senone hidden Markov models)'''
    def __init__(self, modeldir):
        '''USAGE: hfst=Hfst(logdir)'''
        self.modeldir = modeldir
        os.makedirs(logdir, exist_ok=True)
        
    def train_mono(self, corpus, langdir, kaldi_cmd):
        cmd=['local/train_mono.sh','--nj',str(kaldi_cmd.nproc),'--cmd',
             kaldi_cmd.train_cmd, corpus.datadir(),
             langdir, self.modeldir ]
        kaldi.convert_if_newer(os.path.join(langdir,'L.fst'),os.path.join(self.modeldir,'final.mdl'),
                               cmd, sys.stdout, sys.stderr)

                
########## C fst ##################################################
class Cfst:
    '''This class defines a C FST (a mapping from triphones or senones to phones)'''
    def __init__(self, tree):
        '''USAGE: cfst=Cfst(tree)'''
        self.tree = tree
        


########## L fst ##################################################
class Lfst:
    '''This class defines an L FST (a lexicon, i.e., a mapping from phones to words)'''
    def __init__(self,lexicon,nonsilence_phones=[],silence_phones=[],extra_questions=[],optional_silence=[]):
        '''USAGE: L = Lfst(lexicon,...)  
        lexicon: a dict, or a filename
        nonsilence_phones: a list of strings, or a filename
        silence_phones, extra_questions, optional_silence: likewise
        '''
        self.lexicon=lexicon
        self.nonsilence_phones = nonsilence_phones
        self.silence_phones = silence_phones
        self.extra_questions = extra_questions
        self.optional_silence = optional_silence

    def read_lexicons(self):
        '''Read lexicon and phone definitions from files, into dict and list data'''
        lexicon = kaldi.read_dict_from_file(self.lexicon) if isinstance(self.lexicon,str) else self.lexicon
        nonsilence_phones = kaldi.read_list_from_file(self.nonsilence_phones) if isinstance(self.nonsilence_phones,str) else self.nonsilence_phones
        silence_phones = kaldi.read_list_from_file(self.silence_phones) if isinstance(self.silence_phones,str) else self.silence_phones
        extra_questions = kaldi.read_list_from_file(self.extra_questions) if isinstance(self.extra_questions,str) else self.extra_questions
        optional_silence = kaldi.read_list_from_file(self.optional_silence) if isinstance(self.optional_silence,str) else self.optional_silence
        return(Lfst(lexicon,nonsilence_phones,silence_phones,extra_questions,optional_silence))

    def write_to_dictdir(self, dictdir):
        '''Write the lexicon and all phone files to dictdir'''
        other=Lfst(lexicon=os.path.join(dictdir,'lexicon.txt'),
                   nonsilence_phones=os.path.join(dictdir,'nonsilence_phones.txt'),
                   silence_phones=os.path.join(dictdir,'silence_phones.txt'),
                   extra_questions=os.path.join(dictdir,'extra_questions.txt'),
                   optional_silence=os.path.join(dictdir,'optional_silence.txt'))
        lexicon = kaldi.read_dict_from_file(self.lexicon) if isinstance(self.lexicon,str) else self.lexicon
        kaldi.write_dict_to_file(lexicon, other.lexicon)
        nonsilence_phones = kaldi.read_list_from_file(self.nonsilence_phones) if isinstance(self.nonsilence_phones,str) else self.nonsilence_phones
        kaldi.write_list_to_file(nonsilence_phones, other.nonsilence_phones, '\n')
        silence_phones = kaldi.read_list_from_file(self.silence_phones) if isinstance(self.silence_phones,str) else self.silence_phones
        kaldi.write_list_to_file(silence_phones, other.silence_phones, '\n')
        extra_questions = kaldi.read_list_from_file(self.extra_questions) if isinstance(self.extra_questions,str) else self.extra_questions
        kaldi.write_list_to_file(extra_questions, other.extra_questions, ' ')
        optional_silence = kaldi.read_list_from_file(self.optional_silence) if isinstance(self.optional_silence,str) else self.optional_silence
        kaldi.write_list_to_file(optional_silence, other.optional_silence, ' ')
        return(other)

    def dictdir(self):
        '''Return the directoryname in which lexicon occurs, if lexicon is a str, else raise error'''
        if isinstance(self.lexicon,str):
            (dictdir, dictfile) = os.path.split(self.lexicon)
            return(dictdir)
        else:
            raise ValueError(__name__+': lexicon is not a filename, it is {}'.format(self.lexicon))
        
    def lexicon2fst(self,lexiconp, language, oov_word, langdir):
        if os.path.exists(lexiconp) and os.path.getmtime(self.lexicon) > os.path.getmtime(lexiconp):
            os.remove(lexiconp)
        dictdir = self.dictdir()
        cmd=['utils/prepare_lang.sh',dictdir,oov_word, os.path.join(langdir,'tmp'), langdir]
        kaldi.convert_if_newer(self.lexicon, os.path.join(langdir,'L_disambig.fst'),cmd,sys.stdout,sys.stderr)

    
########## G FST ##################################################
class Gfst:
    '''This class defines a G FST (a word-level grammar or language model)'''
    def __init__(self, lm, words):
        '''USAGE: G=Gfst(lm, words).  lm and words must both be filenames.'''
        self.lm = lm
        self.words = words
        
    def move_to_langdir(self, langdir):
        '''Create a new Gfst with files in langdir'''
        other = Gfst(lm=os.path.join(langdir,'lm.arpa.gz'),words=os.path.join(langdir,'words.txt'))
        if kaldi.newer_than(self.lm, other.lm):
            shutil.copy2(self.lm, other.lm)
            (basename, ext) = os.path.splitext(other.lm)
            if ext != 'gz':
                subprocess.run(['gzip',other.lm])
                other.lm += '.gz'
        if kaldi.newer_than(self.words,other.words):
            shutil.copy2(self.words,other.words)
        return(other)
            
    def langdir(self):
        '''Return the directoryname in which lm occurs, if lm is a str, else raise error'''
        if isinstance(self.lm,str):
            (langdir, lmfile) = os.path.split(self.lm)
            return(langdir)
        else:
            raise ValueError(__name__+': lexicon is not a filename, it is {}'.format(self.lexicon))
        
    def lm2fst(self, lexicon):
        langdir=self.langdir()
        cmd=['format_lm.sh',langdir, self.lm, lexicon, langdir ]
        kaldi.convert_if_newer(self.lm, os.path.join(langdir,'G.fst'), cmd, sys.stdout, sys.stderr)

            
########## HCLG Object ##################################################
class HCLG:
    '''This class contains methods to train and test an HCLG speech recognizer'''
    def __init__(self, H, C, L, G):
        '''USAGE: hclg=HCLG(H, C, L, G)'''
        self.H = H
        self.C = C
        self.L = L
        self.G = G
        
    def mkgraph(self):
        '''Compile the graph specified by H, C, L, and G'''
        graphdir = os.path.join(self.H.modeldir, 'graph')
        os.makedirs(graphdir, exist_ok=True)
        cmd=['utils/mkgraph.sh', self.G.langdir(), self.H.modeldir, graphdir]
        subprocess.run(cmd)
        return(graphdir)
    
    def decode(self, graphdir, corpus, logdir, kaldi_cmd):
        cmd=['steps/decode.sh','--nj',str(kaldi_cmd.nproc),'--cmd',kaldi_cmd.decode_cmd,graphdir,
             corpus.datadir(),logdir]
        subprocess.run(cmd)

                

                   

