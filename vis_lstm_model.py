import tensorflow as tf
import math
import drnn

class Vis_lstm_model:
	def init_weight(self, dim_in, dim_out, name=None, stddev=1.0):
		return tf.Variable(tf.truncated_normal([dim_in, dim_out], stddev=stddev/math.sqrt(float(dim_in))), name=name)

	def init_bias(self, dim_out, name=None):
		return tf.Variable(tf.zeros([dim_out]), name=name)

	def __init__(self, options):
		with tf.device('/gpu:0'):
			self.options = options
			#self.logits = None
			
			# +1 for zero padding
			self.Wemb = tf.Variable(tf.random_uniform([options['q_vocab_size'] + 1, options['embedding_size']], -1.0, 1.0), name = 'Wemb')
			self.Wimg = self.init_weight(options['fc7_feature_length'], options['embedding_size'], name = 'Wimg')
			self.bimg = self.init_bias(options['embedding_size'], name = 'bimg')
			

			self.ans_sm_W = self.init_weight(options['rnn_size'], options['ans_vocab_size'], name = 'ans_sm_W')
			self.ans_sm_b = self.init_bias(options['ans_vocab_size'], name = 'ans_sm_b')

	def forward_pass_lstm(self, word_embeddings):
		x = word_embeddings
		output = drnn.drnn_layer_final(x,[512,512],[1,2],self.options['lstm_steps'],input_dims=512)
		return output


	def build_model(self):
		fc7_features = tf.placeholder('float32',[ None, self.options['fc7_feature_length'] ], name = 'fc7')
		sentence = tf.placeholder('int32',[None, self.options['lstm_steps'] - 1], name = "sentence")
		answer = tf.placeholder('float32', [None, self.options['ans_vocab_size']], name = "answer")


		word_embeddings = []
		for i in range(self.options['lstm_steps']-1):
			word_emb = tf.nn.embedding_lookup(self.Wemb, sentence[:,i])
			word_emb = tf.nn.dropout(word_emb, self.options['word_emb_dropout'], name = "word_emb" + str(i))	
			word_embeddings.append(word_emb)
		image_embedding = tf.matmul(fc7_features, self.Wimg) + self.bimg
		image_embedding = tf.nn.tanh(image_embedding)
		image_embedding = tf.nn.dropout(image_embedding, self.options['image_dropout'], name = "vis_features")

		# Image as the last word in the lstm
		word_embeddings.append(image_embedding)
		#self.logits = word_embeddings
		lstm_output = self.forward_pass_lstm(word_embeddings)
		
		lstm_answer = lstm_output[-1]
		logits = tf.matmul(lstm_answer, self.ans_sm_W) + self.ans_sm_b
		# ce = tf.nn.softmax_cross_entropy_with_logits(logits, answer, name = 'ce')
		ce = tf.nn.softmax_cross_entropy_with_logits(labels=answer, logits= logits, name = 'ce')
		answer_probab = tf.nn.softmax(logits, name='answer_probab')
		
		predictions = tf.argmax(answer_probab,1)
		correct_predictions = tf.equal(tf.argmax(answer_probab,1), tf.argmax(answer,1))
		accuracy = tf.reduce_mean(tf.cast(correct_predictions, tf.float32))

		loss = tf.reduce_sum(ce, name = 'loss')
		input_tensors = {
			'fc7' : fc7_features,
			'sentence' : sentence,
			'answer' : answer
		}
		return input_tensors, loss, accuracy, predictions

	def build_generator(self):
		fc7_features = tf.placeholder('float32',[ None, self.options['fc7_feature_length'] ], name = 'fc7')
		sentence = tf.placeholder('int32',[None, self.options['lstm_steps'] - 1], name = "sentence")

		word_embeddings = []
		for i in range(self.options['lstm_steps']-1):
			word_emb = tf.nn.embedding_lookup(self.Wemb, sentence[:,i])
			word_embeddings.append(word_emb)

		image_embedding = tf.matmul(fc7_features, self.Wimg) + self.bimg
		image_embedding = tf.nn.tanh(image_embedding)

		word_embeddings.append(image_embedding)
		lstm_output = self.forward_pass_lstm(word_embeddings)
		lstm_answer = lstm_output[-1]
		logits = tf.matmul(lstm_answer, self.ans_sm_W) + self.ans_sm_b
		
		answer_probab = tf.nn.softmax(logits, name='answer_probab')
		
		predictions = tf.argmax(answer_probab,1)

		input_tensors = {
			'fc7' : fc7_features,
			'sentence' : sentence
		}

		return input_tensors, predictions, answer_probab


