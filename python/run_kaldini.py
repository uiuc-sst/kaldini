#!/usr/bin/python3
"""
USAGE: python run_kaldini.py language
  If called from the command line, this creates an HCLG object with specified language and corpus,
  accessing Kaldi from the specified kaldi_root and SRILM from the specified path,
  then trains and tests it with default settings from those directories.
  [language] = experimental results will be stored in exp/[language]/... and data/[language]/...
  [corpus] = directory containing the subdirectories audio and list, and the file transcription.txt.
  [kaldi_root] = directory containing the subdirectories tools and src.
  [srilm_path] = directory containing the binary executable file ngram-count.
"""

import os, sys, re
import kaldi
import HCLG
import SpeechCorpus

########## Called from the operating system ##################################################
if __name__=="__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        exit(0)
    progname=sys.argv[0]
    language=sys.argv[1]
    corpus_dir=os.path.join('/Users','jhasegaw','data','2018jul','2018-07-07_NI_all_'+language)
    materials_dir=os.path.join('/Users','jhasegaw','data','2018jul',language+'_materials')
    
    # Define the path to Kaldi programs
    kaldi.set_path('/Users/jhasegaw/d/packages/kaldi', '/Users/jhasegaw/d/packages/srilm/bin/macosx')
    kaldi_cmd = kaldi.CMD(nproc=2, train_cmd='run.pl', decode_cmd='run.pl')
    
    # Read the input transcription file, assume it contains all transcriptions
    transcription_file = os.path.join(corpus_dir,'transcription.txt')
    if not os.path.isfile(transcription_file):
        raise FileNotFoundError('No transcription file in {}'.format(transcription_file))
    utt2txt = kaldi.read_dict_from_file(transcription_file)
    print('Read transcriptions from {}'.format(transcription_file))

    # Read the list of all audio files
    audio_dir = os.path.join(corpus_dir,'out')
    files = [ os.path.join(audio_dir,f) for f in os.listdir(audio_dir) if
              re.search(r'\.(wav|flac)',f,flags=re.I) and
              os.path.isfile(os.path.join(audio_dir,f))
    ]
    if len(files) < 10:
        raise FileNotFoundError('Fewer than 10 (wav|flac) files found in {}'.format(audio_dir))
    utt2wav = { SpeechCorpus.get_utt_from_filename(x):x for x in files }

    # Find the set intersection of utterances in utt2txt and utt2wav.  Create an utt2spk dict.
    utts = list(set.intersection(set(utt2wav.keys()), set(utt2txt.keys())))
    utt2spk = { k:SpeechCorpus.get_spk_from_utt(k) for k in utts }

    # Tell the user what we've done.
    print('Found {} utterances, which is the intersection between'.format(len(utts)))
    print('    {} in {}'.format(len(utt2txt),transcription_file))
    print('    and {} in {}'.format(len(utt2wav),audio_dir))
    train_utts = utts[0:int(0.8*len(utts))]
    dev_utts = utts[int(0.8*len(utts)):int(0.9*len(utts))]
    eval_utts = utts[int(0.9*len(utts)):int(1.0*len(utts))]
    print('    Example utt2txt mapping: {}'.format(list(utt2txt.items())[0]))
    print('    Example utt2wav mapping: {}'.format(list(utt2wav.items())[0]))
    print('    Example utt2spk mapping: {}\t{}'.format(utts[0], utt2spk[utts[0]]))
    print('')
    
    # Create the three input corpora
    icorp = {}
    icorp['train'] = SpeechCorpus.corpus(utt2wav={ u:utt2wav[u] for u in train_utts },
                                                utt2spk={ u:utt2spk[u] for u in train_utts },
                                                utt2txt={ u:utt2txt[u] for u in train_utts })
    print('    Train corpus is utts {} to {}'.format(train_utts[0],train_utts[-1]))
    icorp['dev'] = SpeechCorpus.corpus(utt2wav={ u:utt2wav[u] for u in dev_utts },
                                              utt2spk={ u:utt2spk[u] for u in dev_utts },
                                              utt2txt={ u:utt2txt[u] for u in dev_utts })
    print('    Dev corpus is utts {} to {}'.format(dev_utts[0],dev_utts[-1]))
    icorp['eval'] = SpeechCorpus.corpus(utt2wav={ u:utt2wav[u] for u in eval_utts },
                                               utt2spk={ u:utt2spk[u] for u in eval_utts },
                                               utt2txt={ u:utt2txt[u] for u in eval_utts })
    print('    Eval corpus is utts {} to {}'.format(eval_utts[0],eval_utts[-1]))
    
    # Create the input corpora, then downsample, then convert to MFCC
    corpora = {}
    for subc in ('train', 'dev', 'eval'):
        print('Preprocessing {}...'.format(subc))
        datadir=os.path.join(os.getcwd(),'data',language,subc)
        logdir=os.path.join(os.getcwd(), 'exp', language, subc)
        ds_logdir=os.path.join(logdir,'downsample')
        ds_wavdir=os.path.join(datadir,'wav')
        print('    Downsampling to %s'%ds_wavdir)
        print('       logs in %s'%ds_logdir)
        ds_corpus = icorp[subc].downsample(fs=8000,wavdir=ds_wavdir,logdir=ds_logdir)
        print('    Writing %s/{wav.scp,utt2spk,spk2utt,text}'%datadir)
        fi_corpus = ds_corpus.write_dicts_to_dictfiles(utt2wav=os.path.join(datadir,'wav.scp'),
                                                       utt2spk=os.path.join(datadir,'utt2spk'),
                                                       spk2utt=os.path.join(datadir,'spk2utt'),
                                                       utt2txt=os.path.join(datadir,'text'))
        mfcdir=os.path.join(datadir,'mfcc')
        mf_logdir = os.path.join(logdir,'make_mfcc')
        print('    Converting to MFCC in %s'%mfcdir)
        print('       logs in {}'.format(mf_logdir))
        corpora[subc] = fi_corpus.make_mfcc(kaldi_cmd=kaldi_cmd,logdir=mf_logdir,mfccdir=mfcdir)
        cmvn_logdir = os.path.join(logdir,'compute_cmvn_stats')
        print('    Computing CMVN statistics, logs in {}'.format(cmvn_logdir))
        corpora[subc].compute_cmvn_stats(logdir=cmvn_logdir, mfccdir=mfcdir)

    # Create the L, with a given lexicon
    LG_base = '2018-07-02_%s_cog' % language
    L1 = HCLG.Lfst(lexicon=os.path.join(materials_dir,'dict','%s_lexicon.txt'%LG_base),
                   nonsilence_phones=os.path.join(materials_dir,'dict','%s_phones.txt'%LG_base),
                   silence_phones=['sil','laughter','noise','oov'],
                   extra_questions=['sil','laughter','noise','oov'],
                   optional_silence=['sil'])
    L2 = L1.read_lexicons()
    L2.lexicon['<unk>'] = 'oov'
    dictdir=os.path.join(os.getcwd(),'data',language,'dict')
    L3 = L2.write_to_dictdir(dictdir)
    lexiconp = os.path.join(dictdir,'lexiconp.txt')
    langdir=os.path.join(os.getcwd(),'data',language,'lang')
    L3.lexicon2fst(lexiconp=lexiconp,language=language,oov_word='<unk>',langdir=langdir)

    # Create the G, with a given language model
    G1 = HCLG.Gfst(lm=os.path.join(materials_dir,'lang','%s_lm.arpa.gz'%LG_base),
                   words=os.path.join(materials_dir,'lang','%s_words.txt'%LG_base))
    G2 = G1.move_to_langdir(langdir)
    G2.lm2fst(L3.lexicon)
    
    # For monophone: C is null
    C1 = HCLG.Cfst(tree={})
                
    # Monophone training.
    modeldir = os.path.join(os.getcwd(), 'exp', language, 'mono')
    H1 = HCLG.Hfst(modeldir=modeldir)
    H1.train_mono(corpus=corpora['train'], langdir=G2.langdir(), kaldi_cmd=kaldi_cmd)

    # Decode the dev data
    logdir = os.path.join(modeldir,'decode_dev')
    hclg = HCLG.HCLG(H=H1,C=C1,L=L3, G=G2)
    graphdir = hclg.mkgraph()
    hclg.decode(graphdir=graphdir, corpus=corpora['dev'], logdir=logdir, kaldi_cmd=kaldi_cmd)
