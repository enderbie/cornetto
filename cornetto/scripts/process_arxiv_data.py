import numpy as np
import pandas as pd
import re

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from modules.container_builders import VocabBuilder as VB
from modules.container_builders import PhraseBuilder as PB
from modules.container_builders import TFIDFBuilder as TFB
from modules.arxiv_processor import PrepareInput, MSCCleaner
from modules.containers import VocabParams, MSC
from modules.text_processor import TextCleaner, WordSelector

from sklearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import MultiLabelBinarizer


ARXIV_DATA_PATH = '../data/arxiv/'
ARXIV_FILE = '-arxiv_60000.pkl'
INPUT_ = 'Abstract'
OUTPUT_ = 'MSCs'
VOCAB_DIR = '-vocab'
ARXIV_PROC_DIR = '-arxiv_processed'
PHRASE_PERCENT = 0.7
DEPTH = 5

def read_data():
    print("Reading data...")
    df = pd.read_pickle(ARXIV_DATA_PATH+ARXIV_FILE)[[INPUT_, OUTPUT_]]
    return df

class DataFrameSelector(BaseEstimator, TransformerMixin):
    """Returns series from pandas dataframe."""
    def __init__(self, column):
        self.column = column
    def fit(self, X, y=None):
        return self
    def transform(self, X, y=None):
        return X[self.column]

class AbstractCleaner(BaseEstimator, TransformerMixin):
    """
    Given a pandas series of abstracts, returns a list of strings which
    have been cleaned of math expressions.
    """

    def __init__(self, math_replacement=''):
        self.math_replacement = math_replacement

    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):
        f = lambda abstract: TextCleaner.get_clean_words(abstract)
        return X.apply(f)

class VocabSelector(BaseEstimator, TransformerMixin):

    def __init__(self):
        pass

    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):
        temp_vocab = VocabSelector._build_vocab(X)
        phrases = VocabSelector._build_phrases(X, temp_vocab)

        phrases_vocab = phrases.to_vocab()
        vocab = temp_vocab + phrases_vocab

        return vocab

    @staticmethod
    def _build_vocab(sentences):
        print("Building the vocabulary.")
        params = VocabParams.Values()
        vb = VB(params)
        vocab = vb.from_sentences(sentences)
        return vocab

    @staticmethod
    def _build_phrases(sentences, vocab):
        print("Building phrases.")
        pb = PB(vocab)
        p = PHRASE_PERCENT
        phrases = pb.from_sentences(sentences, percentage=p)
        return phrases

if __name__ == "__main__":

    arxiv = read_data()

    target_pipeline = Pipeline([
            ('selector'       , DataFrameSelector(OUTPUT_) ),
            ('cleaner'        , MSCCleaner(depth=DEPTH)),
        ])

    msc_series = target_pipeline.fit_transform(arxiv)

    cleaner_pipeline = Pipeline([
            ('selector'  , DataFrameSelector(INPUT_) ),
            ('cleaner'   , AbstractCleaner()),
        ])

    sentences_series = cleaner_pipeline.fit_transform(arxiv)

    # split pipeline
    vocab_pipeline = Pipeline([
            ('vocab_builder', VocabSelector() ),
    ])

    vocab = vocab_pipeline.fit_transform(sentences_series)
    vocab.save(VOCAB_DIR)

    # update the input of the df by picking the words from vocab and
    # creating phrases by joining words with '_'
    # TODO rename this class to be more desciptive
    series_with_phrases = PrepareInput.from_series(sentences_series, vocab)

    arxiv_processed = pd.concat([series_with_phrases, msc_series], axis=1)

    arxiv_processed = arxiv_processed.drop(arxiv_processed.loc[msc_series.apply(len)==0].index)
    arxiv_processed = arxiv_processed.drop(arxiv_processed.loc[series_with_phrases.apply(len)<10].index)

    pd.to_pickle(arxiv_processed, ARXIV_PROC_DIR + '.pkl')