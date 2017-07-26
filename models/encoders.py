'''
Sentence encoders.

Created on Jul 25, 2017

@author: gcampagn
'''

import tensorflow as tf

class BaseEncoder(object):
    '''
    Base class for an operation that takes a sentence
    (embedded in a some high dimensional vector space) and
    produces a dense representation of it
    '''
    
    def __init__(self, embed_size, output_size, dropout):
        self._embed_size = embed_size
        self._output_size = output_size
        self._dropout = dropout
    
    @property
    def output_size(self):
        return self._output_size
    
    @property
    def embed_size(self):
        return self._embed_size
    
    def encode(self, inputs : tf.Tensor, input_length : tf.Tensor):
        '''
        Encode the given sentence
        
        Args:
            inputs: a tf.Tensor of shape [batch_size, max_time, embed_size]
            input_length: a tf.Tensor of shape [batch_size] and dtype tf.int32
            
        Returns:
            A tuple (enc_hidden_states, enc_final_states), where
            enc_hidden_states is a tensor of shape [batch_size, max_time, output_size]
            and enc_final_states a tensor of shape [batch_size, output_size]
        '''
        raise NotImplementedError


class RNNEncoder(BaseEncoder):
    '''
    Use an RNN to encode the sentence
    '''

    def __init__(self, cell_type, num_layers, *args, **kw):
        super().__init__(*args, **kw)
        self._num_layers = num_layers
        self._cell_type = cell_type
    
    def _make_rnn_cell(self, i):
        if self._cell_type == "lstm":
            cell = tf.contrib.rnn.LSTMCell(self.output_size)
        elif self._cell_type == "gru":
            cell = tf.contrib.rnn.GRUCell(self.output_size)
        elif self._cell_type == "basic-tanh":
            cell = tf.contrib.rnn.BasicRNNCell(self.output_size)
        else:
            raise ValueError("Invalid RNN Cell type")
        cell = tf.contrib.rnn.DropoutWrapper(cell, output_keep_prob=self._dropout, seed=8 + 33 * i)
        return cell
    
    def encode(self, inputs, input_length):
        with tf.name_scope('LSTMEncoder'):
            cell_enc = tf.contrib.rnn.MultiRNNCell([self._make_rnn_cell(i) for i in range(self._num_layers)])
            #cell_enc = tf.contrib.rnn.AttentionCellWrapper(cell_enc, 5, state_is_tuple=True)

            return tf.nn.dynamic_rnn(cell_enc, inputs, sequence_length=input_length,
                                    dtype=tf.float32)


class BagOfWordsEncoder(BaseEncoder):
    '''
    Use a bag of words model to encode the sentence
    '''
    
    def __init__(self, cell_type, *args, **kw):
        super().__init__(*args, **kw)
        self._cell_type = cell_type
    
    def encode(self, inputs, input_length):
        with tf.variable_scope('BagOfWordsEncoder'):
            W = tf.get_variable('W', (self.embed_size, self.output_size))
            b = tf.get_variable('b', shape=(self.output_size,), initializer=tf.constant_initializer(0, tf.float32))

            enc_hidden_states = tf.tanh(tf.tensordot(inputs, W, [[2], [0]]) + b)
            enc_final_state = tf.reduce_sum(enc_hidden_states, axis=1)

            #assert enc_hidden_states.get_shape()[1:] == (self.config.max_length, self.config.hidden_size)
            if self._cell_type == 'lstm':
                enc_final_state = (tf.contrib.rnn.LSTMStateTuple(enc_final_state, enc_final_state),)
        
            return enc_hidden_states, enc_final_state