"""
#Breakdown of Code...

#Notes mentioned in code...

"""
from nltk.collocations import BigramCollocationFinder
from nltk.corpus import stopwords
from nltk.metrics import BigramAssocMeasures
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.collocations import TrigramCollocationFinder
from nltk.metrics import TrigramAssocMeasures
from gensim.models import KeyedVectors
import nltk  # Importing nltk as "import nltk.pos_tag" wasn't working (?)
import spacy

from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from gensim.models import Phrases

from itertools import groupby
import itertools
import re
from pathlib import Path
import RAKE as rake
from collections import Counter
import pke
import operator
from functools import reduce

import numpy as np
from scipy import spatial
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE

import pandas as pd
import string

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.axes3d import get_test_data
from mpl_toolkits import mplot3d
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d import proj3d

from collections import defaultdict
from pprint import pprint
import tensorflow as tf
import tensorflow_hub as hub
from sklearn.cluster import DBSCAN
import importlib
topics = importlib.import_module("msci-project.src.topics")

from InferSent.models import InferSent
import torch
import sys
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
import unicodedata
# from msci-project.src.topics import make_similarity_matrix, plot_similarity

## Pre-processing Functions...

def Preprocess_Content(content):
    """Function"""
    nlp = spacy.load('en', disable=['parser', 'ner'])
    doc = nlp(content)
    content_lemma = " ".join([token.lemma_ for token in doc]) #note this will replace any detected pronoun with '-PRON-'
    content_lemma = re.sub(r'-PRON-', "", content_lemma)

    return content_lemma

def Prep_Content_for_Ngram_Extraction(content):
    """
    Given raw 'content' read in from .txt transcript, process into a list of lower case words
    from which useful bigrams and trigrams can be extracted.
    """
    content_tokenized = word_tokenize(content)
    words = [w.lower() for w in content_tokenized]
    return words

def Extract_bigrams(words):
    """
    Function to extract interesting bigrams used in the vocabulary of a podcast. Input is a list of words
    from the podcast transcript.
    """
    stopset = set(stopwords.words('english'))
    filter_stops = lambda w: len(w) < 3 or w in stopset

    bcf = BigramCollocationFinder.from_words(words)
    bcf.apply_word_filter(filter_stops)               # Ignore bigrams whose words contain < 3 chars / are stopwords
    bcf.apply_freq_filter(3)                          # Ignore trigrams which occur fewer than 3 times in the transcript
    bigrams_extracted = list(list(set) for set in bcf.nbest(BigramAssocMeasures.likelihood_ratio, 20)) # Considering top 20
    final_bigrams = []
    for bigram_list in bigrams_extracted:
        bigram_0, bigram_1 = bigram_list
        bigram_condensed = str(bigram_0 + '_' + bigram_1)
        final_bigrams.append(bigram_condensed)
    print('Bigrams: ', final_bigrams)
    return final_bigrams

def Extract_trigrams(words):
    """
    Function to extract interesting trigrams used in the vocabulary of a podcast. Input is a list of words
    from the podcast transcript.
    """
    stopset = set(stopwords.words('english'))
    filter_stops = lambda w: len(w) < 3 or w in stopset

    tcf = TrigramCollocationFinder.from_words(words)
    tcf.apply_word_filter(filter_stops)               # Ignore trigrams whose words contain < 3 chars / are stopwords
    tcf.apply_freq_filter(3)                          # Ignore trigrams which occur fewer than 3 times in the transcript
    trigrams_extracted = list(list(set) for set in tcf.nbest(TrigramAssocMeasures.likelihood_ratio, 20)) # Considering top 20
    final_trigrams = []
    for trigram_list in trigrams_extracted:
        trigram_0, trigram_1, trigram_2 = trigram_list
        trigram_condensed = str(trigram_0 + '_' + trigram_1 + '_' + trigram_2)
        final_trigrams.append(trigram_condensed)
    print('Trigrams: ', final_trigrams)
    return final_trigrams

def Replace_ngrams_In_Text(content, bigrams_list, trigrams_list):
    """
    Function to replace all cases of individual words from detected n-grams with their respective bi/trigram.
    Returns the document content as a list of words.

    Note why trigrams were replaced first:
    ['brain', 'simulation'] was a detected bigram, and ['deep', 'brain', 'simulation'] was a detected trigram. If
    I condensed all the words 'brain' and 'simulation' into 'brain_simulation' then once I searched for the trigrams
    there would be none left, as it would instead have 'deep', 'brain_simulation'.
    """
    list_of_condensed_grams = []
    content_tokenized = word_tokenize(content)

    # Replace Trigrams...
    for trigram in trigrams_list:
        trigram_0, trigram_1, trigram_2 = trigram
        trigram_condensed = str(trigram_0.capitalize() + '_' + trigram_1.capitalize() + '_' + trigram_2.capitalize())
        list_of_condensed_grams.append(trigram_condensed)
        indices = [i for i, x in enumerate(content_tokenized) if x.lower() == trigram_0
                   and content_tokenized[i+1].lower() == trigram_1
                   and content_tokenized[i+2].lower() == trigram_2]
        for i in indices:
            content_tokenized[i] = trigram_condensed
            content_tokenized[i+1] = '-'              # Placeholders to maintain index numbering - are removed later on
            content_tokenized[i+2] = '-'

    # Replace Bigrams...
    for bigram in bigrams_list:
        bigram_0, bigram_1 = bigram
        bigram_condensed = str( bigram_0.capitalize() + '_' + bigram_1.capitalize())
        list_of_condensed_grams.append(bigram_condensed)
        indices = [i for i, x in enumerate(content_tokenized) if x.lower() == bigram_0
                   and content_tokenized[i+1].lower() == bigram_1]
        for i in indices:
            content_tokenized[i] = bigram_condensed
            content_tokenized[i+1] = '-'                # Placeholders to maintain index numbering - are removed later on

    return content_tokenized

def Preprocess_Sentences(content_sentences):
    """
    Function to preprocess sentences such that they are ready for keyword extraction etc.
    """
    sents_preprocessed = []
    stop_words = set(stopwords.words('english'))
    for sent in content_sentences:
        # Remove numbers
        sent = re.sub(r'\d+', '', sent)
        # Remove punctuation
        sent = re.sub(r'[^\w\s]', '', sent)
        # Make lowercase and remove stopwords
        sent_lower = [w.lower() for w in word_tokenize(sent) if w not in stop_words]
        # Join into one string so can use reg expressions
        result = ' '.join(map(str, sent_lower))
        # Stemming? Lemmatization ?

        sents_preprocessed.append(result)

    return sents_preprocessed

## Keyword Functions...
def Rake_Keywords(content, Info=False):
    """
    Function to extract keywords from document using RAKE
    """
    rake_object = rake.Rake("SmartStoplist.txt")
    keywords = rake_object.run(content)
    if Info:
        print("\nRAKE Keywords:", keywords)

    return keywords

def Counter_Keywords(content_sentences, Info=False):
    """
    Function to extract the top words used in a document using a counter.
    Note these are not 'keywords', just most popular words.
    """
    sents_preprocessed = Preprocess_Sentences(content_sentences)
    sents_preprocessed_flat = reduce(operator.add, sents_preprocessed)
    keywords = Counter(sents_preprocessed_flat).most_common(10)
    if Info:
        print('\nCounter Keywords: ', keywords)

    return keywords

def PKE_keywords(content, number=50, Info=False):
    """
    Function to extract key words and phrases from a document ('content') using the PKE implementation of TopicRank.

    picks up no verbs.
    """
    extractor = pke.unsupervised.TopicRank()
    extractor.load_document(input=content)
    extractor.candidate_selection()
    extractor.candidate_weighting()
    keywords = extractor.get_n_best(number)
    top_keywords = []
    for i in range(len(keywords)):
        top_keywords.append(keywords[i][0])

    # Now join ngram keywords with an underscore
    top_keywords_final = []
    for keyword in top_keywords:
        # see if it is formed of >1 word
        try:
            words = word_tokenize(keyword)
            keyword = '_'.join(words)
            top_keywords_final.append(keyword)
        except:
            top_keywords_final.append(keyword)
    if Info:
        print('Pke Keywords: ', top_keywords_final, '\n')

    return top_keywords_final

def Extract_Nouns(content_sentences, Info=False):
    """
    Function to extract all potentially-interesting nouns from a given document. Used when plotting word embedding.
    before was if pos[0] == 'N'
    'NN' is singular noun, 'NNP' is proper noun, 'FW' is foreign word
    i.e. no NNS or NNPS which are the same but plural..
    was word for (word, pos) in nltk.pos_tag(word_tokenize(sents_preprocessed_flat_onestring))
    """
    nlp = spacy.load("en_core_web_sm")  #en_core_web_sm wasn't detecting verbs well   #en_core_web_lg

    sents_preprocessed = Preprocess_Sentences(content_sentences)
    sents_preprocessed_flat_onestring = ' '.join(sents_preprocessed)
    words_to_plot = [word.text for word in nlp(sents_preprocessed_flat_onestring)
                     if word.pos_ in ['NOUN']
                     and word.text not in ['yeah', 'yes', 'oh', 'i', 'im', 'id', 'thats', 'shes', 'dont',
                                                       'youre', 'theyll', 'youve', 'whats', 'doesnt', 'hes', 'whos',
                                                       'shouldnt']
                     and len(word.text) != 1]

    POSs = [word.pos_ for word in nlp(sents_preprocessed_flat_onestring)
                     if word.pos_ in ['NOUN']
                     and word.text not in ['yeah', 'yes', 'oh', 'i', 'im', 'id', 'thats', 'shes', 'dont',
                                                       'youre', 'theyll', 'youve', 'whats', 'doesnt', 'hes', 'whos',
                                                       'shouldnt']
                     and len(word.text) != 1]

    nouns_to_plot = list(dict.fromkeys(words_to_plot))            # Remove duplicate words

    if Info:
        print('number of nouns extracted with en_core_web_sm (before removing duplicates): ', len(words_to_plot))
        # print('\nExtracted Nouns and POSs: ')
        # for i, j in zip(words_to_plot, POSs):
        #     print(i,j)


    return nouns_to_plot

def Gensim_Phrase():
    """This stuff taken from Inference when was messing around with phrase extraction"""
    phrases = Phrases(content, min_count=2, threshold=3)
    for phrase in phrases[content]:
        print(phrase)
    # Export a FrozenPhrases object that is more efficient but doesn't allow any more training.
    # frozen_phrases = phrases.freeze()
    # print(frozen_phrases[sent]) #give it a sentence like

    # N-GRAM EXTRACTION
    from gensim.models.phrases import Phrases, Phraser

    def build_phrases(sentences):
        phrases = Phrases(sentences,
                          min_count=2,
                          threshold=3,
                          progress_per=1000)
        return Phraser(phrases)

    phrases_model.save('phrases_model.txt')

    phrases_model = Phraser.load('phrases_model.txt')

    def sentence_to_bi_grams(phrases_model, sentence):
        return ' '.join(phrases_model[sentence])


## Word Embedding Functions...
def Convert_bin_to_txt(look_at_vocab=False):
    """
    Function to convert pre-trained word vector files from .bin to .txt format so that can explore vocabulary.
    Only used this function once but keeping in case.
    """
    path_in = 'Google_WordVectors/GoogleNews-vectors-negative300.bin'
    path_out = 'Google_WordVectors/GoogleNews-vectors-negative300.txt'
    model = KeyedVectors.load_word2vec_format(path_in, binary=True)
    model.save_word2vec_format(path_out, binary=False)

    if look_at_vocab:
        model_google = KeyedVectors.load_word2vec_format(path_out, binary=True)
        words = list(model_google.wv.vocab)[:100000]     # Only looking at first hundred thousand
        phrases = [word for word in words if '_' in word]
        print('\nVocab containing an underscore from Google model:', phrases)
    return

def find_closest_embeddings(embeddings_dict):
    return sorted(embeddings_dict.keys(), key=lambda word: spatial.distance.euclidean(embeddings_dict[word], embedding))

def Check_Embedding(embeddings_dict):
    print(find_closest_embeddings(embeddings_dict["king"])[1:6])
    print(find_closest_embeddings(embeddings_dict["twig"] - embeddings_dict["branch"] + embeddings_dict["hand"])[:5])
    #model.most_similar("woman")   model.similarity("girl", "woman")
    return


## Functions for dealing with Keywords...
def Extract_Embeddings_For_Keywords(words_to_extract, embeddings_dict, Info=False):
    """
    Function for extracting the embedding vectors for certain keywords I would like to plot on a word embedding graph.
    By default will extract the embeddings for the top 30 PKE keywords and all potentially-interesting nouns.

    Note A:
        Must check all possible versions of given word (all-capitals, non-capitals, etc) as Google Embeddings
        are inconsistent in form.
    Note B:
        Maybe add a checker of whether the STEM / LEMMA of a word exists
    Note C:
        If multiple possible versions of a given word exists in the embedding vocab, take only the first instance
    """
    words, vectors, words_unplotted = [], [], []
    for word in words_to_extract:
        if "_" in word:                                                      # Note A
            new_word = []
            for i in word.split("_"):
                new_word.append(i.title())
            capitalised_phrase = "_".join(new_word)
            possible_versions_of_word = [word, capitalised_phrase, word.upper()]
        else:
            possible_versions_of_word = [word, word.title(), word.upper()]  # Note B
        if Info:
            print('possible_versions_of_word: ', possible_versions_of_word)
        boolean = [x in embeddings_dict for x in possible_versions_of_word]
        if any(boolean):
            idx = int(list(np.where(boolean)[0])[0])                        # Note C
            true_word = possible_versions_of_word[idx]
            words.append(true_word)
            vectors.append(embeddings_dict[true_word])
        else:
            words_unplotted.append(word)
    if Info:
        print('Number of Words from Document without an embedding: ', len(words_unplotted))
        print('List of Words lacking an embedding:', words_unplotted)
    return words, vectors, words_unplotted

def Extract_Keyword_Vectors(content, content_sentences, Info=False):
    """
    (made on 5th January, works well haven't tested function today (6th) so far though ======)
    Function to extract all types of keywords from transcript + obtain their word embeddings. Only needs to be run once
    then all the keywords + their embeddings are stored in a dataframe 'keyword_vectors_df which is then saved to hdf
    for easy loading in future tasks.

    Note A:
        Currently using GoogleNews pretrained word vectors, but could also use Glove. The benefit of the Google model is
        that it contains vectors for some 'phrases' (bigrams/ trigrams) which is helpful for the plot being meaningful!
    Note B:
        The tsne vector dimensionality must be done all together, but in a way that I can then split the vectors back
        into groups based on keyword type. Hence a little more fiddly.

    """
    if Info:
        print('\n-Extracting keywords + obtaining their word vectors using GoogleNews pretrained model...')

    # Choose pre-trained model... Note A
    Glove_path = r'GloVe/glove.840B.300d.txt'
    Google_path = r'Google_WordVectors/GoogleNews-vectors-negative300.txt'
    path_to_vecs = Google_path

    words = Prep_Content_for_Ngram_Extraction(content)
    if Info:
        print("-Extracted content/sentences/words from transcript.")

    # Get embeddings dictionary of word vectors  from pre-trained word embedding
    embeddings_dict = {}
    if Info:
        print("-Obtaining keyword word vectors using GoogleNews embeddings... (this takes a while)")
    with open(path_to_vecs, 'r', errors='ignore', encoding='utf8') as f:
        try:
            for line in f:
                values = line.split()
                word = values[0]
                vector = np.asarray(values[1:], "float32")
                embeddings_dict[word] = vector
        except:
            f.__next__()
    if Info:
        print("-Obtained all GoogleNews embeddings.")

    # Extract words to plot

    nouns_set = Extract_Embeddings_For_Keywords(Extract_Nouns(content_sentences, Info=True), embeddings_dict)
    pke_set = Extract_Embeddings_For_Keywords(PKE_keywords(content), embeddings_dict)
    bigram_set = Extract_Embeddings_For_Keywords(Extract_bigrams(words), embeddings_dict)
    trigram_set = Extract_Embeddings_For_Keywords(Extract_trigrams(words), embeddings_dict)
    if Info:
        print('-Extracted embeddings for all keywords.')

    # Reduce dimensionality of word vectors such that we can store X and Y positions.
    tsne = TSNE(n_components=2, random_state=0)
    sets_to_plot = [nouns_set, pke_set, bigram_set, trigram_set]

    last_noun_vector = len(nouns_set[0])
    last_pke_vector = last_noun_vector + len(pke_set[0])
    last_bigram_vector = last_pke_vector + len(bigram_set[0])
    last_trigram_vector = last_bigram_vector + len(trigram_set[0])
    all_vectors = list(itertools.chain(nouns_set[1], pke_set[1], bigram_set[1], trigram_set[1]))
    all_keywords = list(itertools.chain(nouns_set[0], pke_set[0], bigram_set[0], trigram_set[0]))

    # Store keywords + embeddings in a pandas data-frame
    keyword_vectors_df = pd.DataFrame(columns = ['noun_keyw',   'noun_X',    'noun_Y', 'unfamiliar_noun',
                                                 'pke_keyw',     'pke_X',    'pke_Y', ' unfamiliar_pke',
                                                 'bigram_keyw',  'bigram_X', 'bigram_Y', 'unfamiliar_bigram',
                                                 'trigram_keyw', 'trigram_X','trigram_Y', 'unfamiliar_trigram'
                                                 ])

    keyword_vectors_df.loc[:, 'noun_keyw'] = pd.Series(nouns_set[0])
    keyword_vectors_df.loc[:, 'unfamiliar_noun'] = pd.Series(nouns_set[2])

    keyword_vectors_df.loc[:, 'pke_keyw'] = pd.Series(pke_set[0])
    keyword_vectors_df.loc[:, 'unfamiliar_pke'] = pd.Series(pke_set[2])

    keyword_vectors_df.loc[:, 'bigram_keyw'] = pd.Series(bigram_set[0])
    keyword_vectors_df.loc[:, 'unfamiliar_bigram'] = pd.Series(bigram_set[2])

    keyword_vectors_df.loc[:, 'trigram_keyw'] = pd.Series(trigram_set[0])
    keyword_vectors_df.loc[:, 'unfamiliar_trigram'] = pd.Series(trigram_set[2])

    reduced_vectors = tsne.fit_transform(all_vectors)                           #Note B

    n = [0, last_noun_vector, last_pke_vector, last_bigram_vector, last_trigram_vector, -1]
    col_names_X, col_names_Y = ['noun_X', 'pke_X', 'bigram_X', 'trigram_X'], ['noun_Y', 'pke_Y', 'bigram_Y', 'trigram_Y']
    for i in range(len(sets_to_plot)):
        Xs = reduced_vectors[n[i]:n[i + 1], 0]
        Ys = reduced_vectors[n[i]:n[i + 1], 1]
        keyword_vectors_df.loc[:, col_names_X[i]] = pd.Series(Xs)
        keyword_vectors_df.loc[:, col_names_Y[i]] = pd.Series(Ys)

    # Store keywords + embeddings in a hd5 file for easy accessing in future tasks.
    keyword_vectors_df.to_hdf('Saved_dfs/keyword_vectors_df.h5', key='df', mode='w')
    if Info:
        print('-Created and saved keyword_vectors_df dataframe.')

    return nouns_set, pke_set, bigram_set, trigram_set

def Find_Keywords_in_Segment(sents_in_segment, all_keywords, Info=False):
    """
    should use regular expressions to make faster
    go segment by segment and look for all the keywords/phrases in it, make it into a list
    """
    keywords_contained_in_segment = {} #keys are keywords, values are the number of ocurrences of the keyword in the seg

    sents_in_subsection_flat = ''.join(list(itertools.chain.from_iterable(sents_in_segment))) # one string
    words_in_subsection = word_tokenize(sents_in_subsection_flat)   #might need to remove punctuation before doing this

    #convert to strings
    all_keywords = [str(word) for word in all_keywords]
    word_list = [word for word in all_keywords if len(word.split('_')) == 1]
    bigram_list = [word for word in all_keywords if len(word.split('_')) == 2]
    trigram_list = [word for word in all_keywords if len(word.split('_')) == 3]

    # Firstly search for all one-word keywords (nouns and pke)
    for word in word_list:
        count = sents_in_subsection_flat.lower().split().count(word)
        if count != 0:
            keywords_contained_in_segment[word] = count

    # Then search for bigrams/trigrams
    for trigram in trigram_list:
        trigram_0, trigram_1, trigram_2 = [w.lower() for w in trigram.split('_')]
        indices = [i for i, x in enumerate(words_in_subsection) if x.lower() == trigram_0
                   and words_in_subsection[i + 1].lower() == trigram_1
                   and words_in_subsection[i + 2].lower() == trigram_2]
        if len(indices) != 0:
            keywords_contained_in_segment[trigram] = len(indices)

    for bigram in bigram_list:
        bigram_0, bigram_1 = [w.lower() for w in bigram.split('_')]
        indices = [i for i, x in enumerate(words_in_subsection) if x.lower() == bigram_0
                   and words_in_subsection[i + 1].lower() == bigram_1]
        if len(indices) != 0:
            keywords_contained_in_segment[bigram] = len(indices)

    if Info:
        print('keywords_contained_in_segment dictionary', keywords_contained_in_segment)

    return keywords_contained_in_segment

## Functions for Segmentation...

def Peform_Segmentation(content_sentences, segmentation_method='Even', Num_Even_Segs=10, cos_sim_limit=0.52):
    """
    Function to segment up a transcript. By default will segment up the transcript into 'Num_Even_Segs' even segments.
    Returns a list containing the indices of the first sentence of each segment, 'first_sent_idxs_list'.
    """
    if segmentation_method == 'InferSent':
        # 1
        # Obtain sentence embeddings using InferSent + create dataframe of consec sents cosine similarity + predict segmentation
        embeddings = Obtain_Sent_Embeddings_InferSent(content_sentences, Info=False)

        # Obtain cosine similarity info dataframe
        cos_sim_df = Calc_CosSim_InferSent(content_sentences, embeddings, cos_sim_limit, Info=True)

        # [OR if embeddings were already obtained, simply load dataframe]
        # cos_sim_df = pd.read_hdf('Saved_dfs/InferSent_cos_sim_df.h5', key='df')

        # 2
        first_sent_idxs_list = []
        df_mini = cos_sim_df[cos_sim_df['New_Section'] == 1]
        for idx, row in df_mini.iterrows():
            first_sent_idxs_list.append(row['Sentence2_idx'])

    if segmentation_method == 'Even':
        def split(a, n):
            k, m = divmod(len(a), n)
            return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))

        num_sents = len(content_sentences)
        idx_split = split(range(num_sents), Num_Even_Segs)
        first_sent_idxs_list = [i[0] for i in idx_split][1:]

    #if SliceCast:
        #

    return first_sent_idxs_list


def get_segments_info(first_sent_idxs_list, content_sentences, keyword_vectors_df, save_name='segments_info_df', Info=False):
    """
    Function to perform segment-wise keyword analysis.
    Collects information about they keywords contained in each segment of the transcript.

    params
     'first_sent_idxs_list':
        List containing the index of sentences which start a new segment.

    Returns a dataframe 'segments_info_df'

    keyword averaging note: If segments are small enough, i.e. only 2-5 utterances at a time, should only really contain a couple of keywords
    that will be (hopefully) semantically similar.

    """
    if Info:
        print('\n-Obtaining information about each segment using cos_sim_df...')

    def getIndexes(dfObj, value):
        ''' Get index positions of value in dataframe i.e. dfObj.'''
        listOfPos = list()
        # Get bool dataframe with True at positions where the given value exists
        result = dfObj.isin([value])
        # Get list of columns that contains the value
        seriesObj = result.any()
        columnNames = list(seriesObj[seriesObj == True].index)
        # Iterate over list of columns and fetch the rows indexes where value exists
        for col in columnNames:
            rows = list(result[col][result[col] == True].index)
            for row in rows:
                listOfPos.append([row, col])
                # listOfPos.append(col)
        # Return a list of tuples indicating the positions of value in the dataframe
        return listOfPos

    all_keywords = list(itertools.chain(keyword_vectors_df['noun_keyw'].values, keyword_vectors_df['pke_keyw'].values,
                                        keyword_vectors_df['bigram_keyw'].values,
                                        keyword_vectors_df['trigram_keyw'].values
                                        ))

    segments_dict = {'first_sent_numbers': [], 'length_of_segment': [], 'keyword_list': [], 'keyword_counts': [],
                     'total_average_keywords_wordvec': [],
                     'top_count_keyword': [], 'top_count_wordvec': [],
                     'top_3_counts_keywords': [], 'top_3_counts_wordvec': []}

    old_idx = 0
    for idx in first_sent_idxs_list:
        # Collect basic information about this segment
        segments_dict['first_sent_numbers'].append(idx)  # POSITION of each section
        length = np.int(idx) - np.int(old_idx)  # LENGTH of each section
        segments_dict['length_of_segment'].append(length)

        # Collect keywords contained in this segment as well as their counts
        sentences_in_segment = content_sentences[old_idx:idx]
        keywords_dict = Find_Keywords_in_Segment(sentences_in_segment, all_keywords, Info=False)
        keywords_list, keywords_count = list(keywords_dict.keys()), list(keywords_dict.values())
        segments_dict['keyword_list'].append(keywords_list)
        segments_dict['keyword_counts'].append(keywords_count)

        # Collect the Word embeddings for the keywords contained in this segment
        df = keyword_vectors_df
        Xvecs, Yvecs = [], []
        for keyword in keywords_list:
            # get index for row and column
            row, col_name = getIndexes(df, keyword)[0]
            col_idx = [idx for idx, val in enumerate(df.columns)][0]
            # get the average vector position  #note !need to make sure columns are in right order
            Xvecs.append(df.iloc[row, col_idx + 1])
            Yvecs.append(df.iloc[row, col_idx + 2])

        # Collect vectors for possible locations to place the node representing each segment
        segments_dict['total_average_keywords_wordvec'].append([np.mean(Xvecs), np.mean(Yvecs)])

        if len(keywords_count) >= 1 :
            idx_of_top_keyword = keywords_count.index(max(keywords_count))
            keywords_list = np.array(keywords_list)
            top_keyword, top_keyword_XY = keywords_list[idx_of_top_keyword], [Xvecs[idx_of_top_keyword],
                                                                          Yvecs[idx_of_top_keyword]]
        else:
            top_keyword = None
            top_keyword_XY = None
        segments_dict['top_count_keyword'].append(top_keyword)
        segments_dict['top_count_wordvec'].append(top_keyword_XY)

        # Check that there are at least 3 keywords for the section
        Xvecs, Yvecs = np.array(Xvecs), np.array(Yvecs)

        if len(keywords_list) >= 3:
            idxs_of_top_3_keywords = sorted(range(len(keywords_count)), key=lambda i: keywords_count[i])[-3:]
            top_3_keywords = keywords_list[idxs_of_top_3_keywords]
            #print('top_3_keywords: ', top_3_keywords)
            top_3_keywords_X, top_3_keywords_Y = Xvecs[idxs_of_top_3_keywords], Yvecs[idxs_of_top_3_keywords]
            segments_dict['top_3_counts_keywords'].append(top_3_keywords)
            segments_dict['top_3_counts_wordvec'].append([np.mean(top_3_keywords_X), np.mean(top_3_keywords_Y)])
        else:
            segments_dict['top_3_counts_keywords'].append(['nan', 'nan', 'nan'])
            segments_dict['top_3_counts_wordvec'].append('nan')

        old_idx = idx

    # Convert dictionary to dataframe
    segments_info_df = pd.DataFrame({k: pd.Series(l) for k, l in segments_dict.items()})
    segments_info_df.to_hdf('Saved_dfs/{}.h5'.format(save_name), key='df', mode='w')
    if Info:
        print('-Created segments_info_df. Preview: ')
        print(segments_info_df.head().to_string())
        print('Lengths of Segments:', segments_dict['length_of_segment'])
        print('#Keywords in each Segment:', [len(words_list) for words_list in segments_dict['keyword_list']])
        print('#Segments with zero keywords:', [len(words_list) for words_list in list(keywords_dict.keys())].count(0))

    return segments_info_df

def Obtain_Sent_Embeddings_InferSent(sentences, V=1, Info=False):
    """
    V = 1 for GloVe, 2 for FastText
    """
    all_combinations = False  # True to compare ALL sentences, False to compare only consecutive sentences
    cutoff = 0.5  # Cutoff value for weighted graph
    # STEP 1
    # Build sentences list...
    # Load pre-processed transcript of interview between Elon Musk and Joe Rogan
    # with open(path, 'r') as f:
    #     content = f.read()
    #     sentences = nltk.sent_tokenize(content)
    if Info:
        print('\nObtaining sentence embeddings with InferSent...')

    # InferSent...
    MODEL_PATH = 'encoder/infersent%s.pkl' % V
    if V == 1:
        W2V_PATH = 'GloVe/glove.840B.300d.txt'
    if V == 2:
        W2V_PATH = 'fastText/crawl-300d-2M.vec'
    params_model = {'bsize': 64, 'word_emb_dim': 300, 'enc_lstm_dim': 2048,
                    'pool_type': 'max', 'dpout_model': 0.0, 'version': V}

    infersent = InferSent(params_model)
    infersent.load_state_dict(torch.load(MODEL_PATH))
    infersent.set_w2v_path(W2V_PATH)
    infersent.build_vocab(sentences, tokenize=True)
    embeddings = infersent.encode(sentences, tokenize=True)

    if Info:
        print('-Obtained sentence embeddings with InferSent.')

    return embeddings

def Calc_CosSim_InferSent(content_sentences, embeddings, cos_sim_limit=0.52, Info=False):
    """
    Function to
    param cos_sim_limit:
        The parameter which will determine the number of segments
        if = 0.6  there are 64 segments
        if = 0.55 there are 25 segments
        if = 0.52 there are 15 segments
        if = 0.5  there are 10 segments
        if = 0.45 there are 3 segments
    """

    def cosine(u, v):
        return np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v))

    tbl = dict.fromkeys(i for i in list(range(sys.maxunicode)) if unicodedata.category(chr(i)).startswith('P'))

    # def remove_punctuation(text):
    #     return text.translate(tbl)
    if Info:
        print('\n-Creating cos_sim_df dataframe...')

    idxs_blank = []
    content_sentences_copy = content_sentences
    cos_sim_df = pd.DataFrame(columns=['Sentence1', 'Sentence1_idx', 'Sentence2', 'Sentence2_idx', 'Cosine_Similarity',
                                       'New_Section'])

    # Firstly, put all sentences of length <5 to blank in a new content_sentences_object (preliminary method to deal with filler sents)
    for idx, sentence in enumerate(content_sentences_copy):
        sentence = sentence.translate(tbl)  # remove_punctuation(sentence)
        num_words = len(word_tokenize(sentence))
        if num_words <= 5:
            content_sentences_copy[idx] = []
            idxs_blank.append(idx)

    idxs_sentences_to_compare = [x for x in list(range(len(content_sentences_copy))) if x not in idxs_blank]
    cnt = 0
    for idx, i in enumerate(idxs_sentences_to_compare):
        if idx == len(idxs_sentences_to_compare) - 1:
            break
        j = idxs_sentences_to_compare[idx + 1]
        sent1, sent2 = content_sentences_copy[i], content_sentences_copy[j]
        cos_sim = cosine(embeddings[i], embeddings[j])
        if cos_sim < cos_sim_limit:
            new_segment = 1
        else:
            new_segment = 0
        cos_sim_df.loc[cnt] = [sent1, i, sent2, j, cos_sim, new_segment]
        cnt += 1

        # if Info:
        #     print('pair', cnt, '/', len(idxs_sentences_to_compare), 'idxs: ', i, 'vs.', j, '        ', cos_sim,
        #           '      ',
        #           sent1, '======', sent2)

    # Save df to hdf
    cos_sim_df.to_hdf('Saved_dfs/InferSent_cos_sim_df.h5', key='df', mode='w')

    if Info:
        print('-Number of segments: ', cos_sim_df.New_Section.value_counts().loc[1])
        print('-Saved Cos_Sim_df to hd5 file. Preview of cos_sim_df:')
        print(cos_sim_df.head().to_string())

    return cos_sim_df

def Cluster_Transcript(content_sentences):
    """
    NOT USING SO FAR.
    Taken from Msci project work that Jonas did on 5th January

    Doesn't segment like i hoped it would - just clusters sentences (in no particular order, i.e. not considering
    whether they are consecutive) so could be used for topic detection but not segmentation.
    """
    #load transcript
    print("-Loading sentence embedder, this takes a while...")
    embed = hub.load("https://tfhub.dev/google/universal-sentence-encoder/4")
    print("Done")

    #embed using google sentence encoder
    embeddings = embed(content_sentences)
    print('Embedded using Google Sentence Encoder')

    #approach 1: use density based clustering algorithm to cluster sentences into topics
    sim_m = topics.make_similarity_matrix(content_sentences, embeddings)

    cluster_labels = DBSCAN(eps=2.2, min_samples=1).fit_predict(sim_m) #eps is sensitivity

    clusters = defaultdict(list)
    for cl, sentence in zip(cluster_labels, content_sentences):
        clusters[cl].append(sentence)
    print('\n list(clusters.values()): ')
    pprint(list(clusters.values())) #these are sentence clusters
    print('\nNumber of Clusters: ', len(list(clusters.values())))

    #find the sentence index at which the clusters start


    #print('\nnow plotting')
    #topics.plot_similarity(content_sentences, embeddings, 90) #visualised here


## Functions for plotting...
def Plot_Wordcloud(content_sentences, save=False):
    """
    Function to plot a 2D Wordcloud from the top words in a given document.
    """
    sents_preprocessed = Preprocess_Sentences(content_sentences)
    sents_preprocessed_flat = reduce(operator.add, sents_preprocessed)
    stop_words = set(stopwords.words('english'))

    wordcloud = WordCloud(background_color='white',
                            stopwords=stop_words,
                            max_words=100,
                            max_font_size=50,
                            random_state=42).generate(str(sents_preprocessed_flat))
    fig = plt.figure()
    plt.imshow(wordcloud)
    plt.axis('off')
    plt.show()
    if save:
        fig.savefig("Saved_Images/WordCloud.png", dpi=900)
    return

def PlotWord_Embeddings(keyword_vectors_df, save_fig=False, Info=False):
    """
    Plots the Word2Vec layout of all the keywords from the podcast. Keywords include those extracted using TopicRank,
    all potentially-interesting nouns, and all extracted bigrams and trigrams. Includes colour coordination with respect
    to the type of keywords.
    """
    if Info:
        print('\n-Plotting Word Embedding for all Keywords...')
    keyword_types = ['noun', 'pke', 'bigram', 'trigram']
    colours = ['blue', 'green', 'orange', 'pink']
    labels = ['Nouns', 'PKE Keywords', 'Bigrams', 'Trigrams']

    plt.figure()

    for i in range(len(keyword_types)):
        type = keyword_types[i]
        words = keyword_vectors_df['{}_keyw'.format(type)]
        Xs, Ys = keyword_vectors_df['{}_X'.format(type)], keyword_vectors_df['{}_Y'.format(type)]
        unplotted = list(keyword_vectors_df['unfamiliar_{}'.format(type)].dropna(axis=0))

        plt.scatter(Xs, Ys, c=colours[i], label=labels[i])
        for label, x, y in zip(words, Xs, Ys):
            plt.annotate(label, xy=(x, y), xytext=(0, 0), textcoords="offset points")
        print('Plotted: ', labels[i])
        print(labels[i], 'which were not plotted due to lack of embedding: ', list(unplotted))

    plt.legend()
    plt.title('Keywords_Embedding')
    if save_fig:
        plt.savefig("Saved_Images/Keyword_Types_WordEmbedding.png")
    plt.show()

    return

def Plot_2D_Topic_Evolution_SegmentWise(segments_info_df, save_name, Node_Position='total_average', save_fig=False):
    """
    Plots the nice 2D word embedding space with an arrow following the direction of the topics discussed in each
    segment of the transcript.
    segments_dict = {'first_sent_numbers': [], 'length_of_segment': [], 'keyword_list': [], 'keyword_counts': [],
                     'total_average_keywords_wordvec': [],
                     'top_count_keyword': [], 'top_count_wordvec': [],
                     'top_3_counts_keywords': [], 'top_3_counts_wordvec': []}
    """

    if Node_Position =='total_average':
        node_position = segments_info_df['total_average_keywords_wordvec'].values
        labels = range(len(node_position))  # numerical labels

    if Node_Position == '1_max_count':
        labels_text = segments_info_df['top_count_keyword'].values
        node_position = segments_info_df['top_count_wordvec'].values

        # Check the segments all had enough keywords to have taken max(count)...
        node_position = [pos for pos in node_position if pos != None]
        labels_text = [label for label in labels_text if label != None]
        labels = range(len(node_position))

    if Node_Position == '3_max_count':
        labels_text = segments_info_df['top_3_counts_keywords'].values
        node_position = segments_info_df['top_3_counts_wordvec'].values

        # Check the segments all had enough keywords to have taken max(count)...
        node_position = [pos for pos in node_position if str(pos[0]) != 'n']
        labels_text = [label for label in labels_text if str(label) != 'nan']
        labels = range(len(node_position))

    xs = [x[0] for x in node_position]
    ys = [x[1] for x in node_position]

    u = [i-j for i, j in zip(xs[1:], xs[:-1])]
    v = [i-j for i, j in zip(ys[1:], ys[:-1])]

    plt.figure()
    plt.quiver(xs[:-1], ys[:-1], u, v, scale_units='xy',
               angles='xy', scale=1, color='b', width=0.005)

    # zip joins x and y coordinates in pairs
    for x, y, label in zip(xs, ys, labels):
        plt.annotate(label+1, # this is the text
                     (x, y), # this is the point to label
                     textcoords="offset points", # how to position the text
                     xytext=(0,10), # distance from text to points (x,y)
                     ha='center') # horizontal alignment can be left, right or center

    #plot special colours for the first and last point
    plt.plot([xs[0]], [ys[0]], 'o', color='green', markersize=10, label='Beginning of Conversation')
    plt.plot([xs[-1]], [ys[-1]], 'o', color='red', markersize=10, label='End of Conversation')
    plt.title(save_name)
    if save_fig:
        plt.savefig("Saved_Images/{}.png".format(save_name), dpi=900)
    plt.show()

    return

def Plot_Quiver_And_Embeddings(segments_info_df, keyword_vectors_df, save_name, Node_Position='total_average',
                               only_nouns=True, save_fig=False):
    """
    Plots BOTH a background of keywords + the 2D quiver arrow following the direction of the topics discussed in each
    segment of the transcript.
    """
    # EMBEDDING PART
    keyword_types = ['noun', 'pke', 'bigram', 'trigram']
    colours = ['pink', 'green', 'orange', 'blue']
    labels = ['Nouns', 'PKE Keywords', 'Bigrams', 'Trigrams']

    number_types_toplot = range(len(keyword_types))
    if only_nouns:
        number_types_toplot = [0]

    plt.figure()
    plt.rc('font', size=8)
    for i in number_types_toplot:
        type = keyword_types[i]
        words = keyword_vectors_df['{}_keyw'.format(type)]
        Xs, Ys = keyword_vectors_df['{}_X'.format(type)], keyword_vectors_df['{}_Y'.format(type)]
        unplotted = list(keyword_vectors_df['unfamiliar_{}'.format(type)].dropna(axis=0))

        plt.scatter(Xs, Ys, c=colours[i], label=labels[i])
        for label, x, y in zip(words, Xs, Ys):
            plt.annotate(label, xy=(x, y), xytext=(0, 0), textcoords="offset points", color='darkgrey')

    plt.rc('font', size=10) # putting it back to normal

    # QUIVER PART
    if Node_Position == 'total_average':
        node_position = segments_info_df['total_average_keywords_wordvec'].values

    if Node_Position == '1_max_count':
        labels_text = segments_info_df['top_count_keyword'].values
        node_position = segments_info_df['top_count_wordvec'].values

        # Check the segments all had enough keywords to have taken max(count)...
        node_position = [pos for pos in node_position if pos != None]
        labels_text = [label for label in labels_text if label != None]

    if Node_Position == '3_max_count':
        labels_text = segments_info_df['top_3_counts_keywords'].values
        node_position = segments_info_df['top_3_counts_wordvec'].values

        # Check the segments all had enough keywords to have taken max(count)...
        node_position = [pos for pos in node_position if str(pos[0]) != 'n']
        labels_text = [label for label in labels_text if str(label) != 'nan']
    labels = range(len(node_position))

    xs = [x[0] for x in node_position]
    ys = [x[1] for x in node_position]

    u = [i-j for i, j in zip(xs[1:], xs[:-1])]
    v = [i-j for i, j in zip(ys[1:], ys[:-1])]

    plt.quiver(xs[:-1], ys[:-1], u, v, scale_units='xy',
               angles='xy', scale=1, color='b', width=0.005)

    # zip joins x and y coordinates in pairs
    for x, y, label in zip(xs, ys, labels):
        plt.annotate(label+1, # this is the text
                     (x, y), # this is the point to label
                     textcoords="offset points", # how to position the text
                     xytext=(0, 10), # distance from text to points (x,y)
                     ha='center') # horizontal alignment can be left, right or center

    #plot special colours for the first and last point
    plt.plot([xs[0]], [ys[0]], 'o', color='green', markersize=10, label='Beginning of Conversation')
    plt.plot([xs[-1]], [ys[-1]], 'o', color='red', markersize=10, label='End of Conversation')
    plt.title(save_name)
    plt.legend()
    if save_fig:
        plt.savefig("Saved_Images/{}.png".format(save_name), dpi=900)
    plt.show()

class Arrow3D(FancyArrowPatch):
    def __init__(self, xs, ys, zs, *args, **kwargs):
        FancyArrowPatch.__init__(self, (0, 0), (0, 0), *args, **kwargs)
        self._verts3d = xs, ys, zs

    def draw(self, renderer):
        xs3d, ys3d, zs3d = self._verts3d
        xs, ys, zs = proj3d.proj_transform(xs3d, ys3d, zs3d, renderer.M)
        self.set_positions((xs[0], ys[0]), (xs[1], ys[1]))
        FancyArrowPatch.draw(self, renderer)

def Plot_3D_Trajectory_through_TopicSpace():
    """
    Taken from my messy code in Inference. Here ready for when I have segmentation info from Jonas' method.
    """
    df_manual = pd.read_hdf('./SGCW/Topic_avs_df_manual.h5', key='dfs')
    labels_manual = df_manual['Topic_Num'].values
    df_slice = pd.read_hdf('./SGCW/Topic_avs_df_slice.h5', key='dfs')
    labels_slice = df_slice['Topic_Num'].values

    # set up a figure twice as wide as it is tall
    fig = plt.figure(figsize=(22, 11))  # plt.figaspect(0.5))
    fig.suptitle('Movement through topic space over time')

    # set up the axes for the first plot
    ax1 = fig.add_subplot(1, 2, 1, projection='3d')

    # Data for a three-dimensional line
    word_emb_xs = df_manual['Av_X'].values
    word_emb_ys = df_manual['Av_Y'].values
    label_seg_df = pd.read_hdf('./SGCW/segs_manual_info.h5', key='dfs')
    segment_numbers = label_seg_df['first_sent_numbers'].values
    print('segment_numbers', segment_numbers)

    #ax.plot3D(xs, segment_numbers, ys, 'bo-')
    ax1.set_xlabel('$time (Segment Number)$', fontsize=13)
    ax1.set_ylabel('$X$', fontsize=20, rotation = 0)
    ax1.set_zlabel('$Y$', fontsize=20)
    ax1.zaxis.set_rotate_label(False)
    ax1.set_title('Manual')

    cnt = 0
    # (old_x, old_y, old_z) = (0, 0, 0)
    for x, y, z, label in zip(segment_numbers, word_emb_xs, word_emb_ys, labels_manual):
      cnt +=1
      ax1.plot([x], [y], [z],'o') #markerfacecolor='k', markeredgecolor='k', marker='o', markersize=5, alpha=0.6)
      ax1.text(x, y, z, label+1, size=10)
      if cnt ==1:
        (old_x, old_y, old_z) = (x, y, z)
        continue

      a = Arrow3D([old_x, x], [old_y,y], [old_z, z], mutation_scale=20, lw=3, arrowstyle="-|>", color="r")
      ax1.add_artist(a)

      (old_x, old_y, old_z) = (x, y, z)


    # AXIS STUFF
    ax1.dist = 13
    ax1 = plt.gca()
    # ax.xaxis.set_ticklabels([])
    ax1.yaxis.set_ticklabels([])
    ax1.zaxis.set_ticklabels([])

    # for line in ax.xaxis.get_ticklines():
    #     line.set_visible(False)
    for line in ax1.yaxis.get_ticklines():
        line.set_visible(False)
    for line in ax1.zaxis.get_ticklines():
        line.set_visible(False)

    fig.show()

##



def Go(path_to_transcript, seg_method, node_location_method, Even_number_of_segments, InferSent_cos_sim_limit, saving_figs):
    """
    Mother Function.
    """
    ## Load + Pre-process Transcript
    with open(path_to_transcript, 'r') as f:
        content = f.read()
        content = Preprocess_Content(content)
        content_sentences = nltk.sent_tokenize(content)

    ## Segmentation
    first_sent_idxs_list = Peform_Segmentation(content_sentences, segmentation_method=seg_method,
                                                Num_Even_Segs=Even_number_of_segments,
                                                cos_sim_limit=InferSent_cos_sim_limit)

    ## Keyword Extraction
    # nouns_set, pke_set, bigram_set, trigram_set = Extract_Keyword_Vectors(content, content_sentences, Info=True)

    # OR just load the dataframe
    keyword_vectors_df = pd.read_hdf('Saved_dfs/keyword_vectors_df.h5', key='df')

    ## Segment-Wise Information Extraction
    if seg_method == 'Even':
        save_name = '{0}_{1}_segments_info_df'.format(Even_number_of_segments, seg_method)
    if seg_method == 'InferSent':
        save_name = 'InferSent_{0}_segments_info_df'.format(InferSent_cos_sim_limit)

    # Create dataframe with the information about the segments
    segments_info_df = get_segments_info(first_sent_idxs_list, content_sentences, keyword_vectors_df,
                                         save_name=save_name, Info=True)

    # OR just load the dataframe
    # segments_info_df = pd.read_hdf('Saved_dfs/{}.h5'.format(save_name), key='df')

    ## Plot Word Embedding
    # PlotWord_Embeddings(keyword_vectors_df, save_fig=False)

    ## Plot Quiver Plot
    if seg_method == 'Even':
        save_name = '{0}_{1}_Segments_Quiver_Plot_With_{2}_NodePosition'.format(Even_number_of_segments,
                                                                                seg_method, node_location_method)
    if seg_method == 'InferSent':
        save_name = 'Infersent_{0}_Segments_Quiver_Plot_With_{1}_NodePosition'.format(InferSent_cos_sim_limit,
                                                                                      node_location_method)
    Plot_2D_Topic_Evolution_SegmentWise(segments_info_df, save_fig=saving_figs, Node_Position=node_location_method,
                                        save_name=save_name)

    ## Plot Quiver + Embedding
    if seg_method == 'Even':
        save_name = '{0}_{1}_Segments_Quiver_and_Embeddings_Plot_With_{2}_NodePosition'.format(Even_number_of_segments,
                                                                                               seg_method,
                                                                                               node_location_method)
    if seg_method == 'InferSent':
        save_name = 'Infersent_{0}_Segments_Quiver_and_Embeddings_Plot_With_{1}_NodePosition'.format(
            InferSent_cos_sim_limit,
            node_location_method)
    Plot_Quiver_And_Embeddings(segments_info_df, keyword_vectors_df, Node_Position=node_location_method,
                               only_nouns=True,
                               save_fig=saving_figs, save_name=save_name)


## CODE...
if __name__=='__main__':

    path_to_transcript = Path('data/shorter_formatted_plain_labelled.txt')

    seg_method = 'Even'                                 #'Even      # 'InferSent'
    node_location_method = '3_max_count'                # 'total_average'    # '1_max_count'     # '3_max_count'

    Even_number_of_segments = 20                       # for when seg_method = 'Even'
    InferSent_cos_sim_limit = 0.52                      # for when seg_method = 'InferSent'

    saving_figs = True


    Go(path_to_transcript, seg_method, node_location_method, Even_number_of_segments, InferSent_cos_sim_limit, saving_figs)

