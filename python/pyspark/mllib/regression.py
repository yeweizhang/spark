#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import numpy as np
from numpy import array

from pyspark import RDD
from pyspark.streaming.dstream import DStream
from pyspark.mllib.common import callMLlibFunc, _py2java, _java2py, inherit_doc
from pyspark.mllib.linalg import SparseVector, Vectors, _convert_to_vector
from pyspark.mllib.util import Saveable, Loader

__all__ = ['LabeledPoint', 'LinearModel',
           'LinearRegressionModel', 'LinearRegressionWithSGD',
           'RidgeRegressionModel', 'RidgeRegressionWithSGD',
           'LassoModel', 'LassoWithSGD', 'IsotonicRegressionModel',
           'IsotonicRegression']


class LabeledPoint(object):

    """
    Class that represents the features and labels of a data point.

    :param label: Label for this data point.
    :param features: Vector of features for this point (NumPy array,
            list, pyspark.mllib.linalg.SparseVector, or scipy.sparse
            column matrix)

    Note: 'label' and 'features' are accessible as class attributes.
    """

    def __init__(self, label, features):
        self.label = float(label)
        self.features = _convert_to_vector(features)

    def __reduce__(self):
        return (LabeledPoint, (self.label, self.features))

    def __str__(self):
        return "(" + ",".join((str(self.label), str(self.features))) + ")"

    def __repr__(self):
        return "LabeledPoint(%s, %s)" % (self.label, self.features)


class LinearModel(object):

    """
    A linear model that has a vector of coefficients and an intercept.

    :param weights: Weights computed for every feature.
    :param intercept: Intercept computed for this model.
    """

    def __init__(self, weights, intercept):
        self._coeff = _convert_to_vector(weights)
        self._intercept = float(intercept)

    @property
    def weights(self):
        return self._coeff

    @property
    def intercept(self):
        return self._intercept

    def __repr__(self):
        return "(weights=%s, intercept=%r)" % (self._coeff, self._intercept)


@inherit_doc
class LinearRegressionModelBase(LinearModel):

    """A linear regression model.

    >>> lrmb = LinearRegressionModelBase(np.array([1.0, 2.0]), 0.1)
    >>> abs(lrmb.predict(np.array([-1.03, 7.777])) - 14.624) < 1e-6
    True
    >>> abs(lrmb.predict(SparseVector(2, {0: -1.03, 1: 7.777})) - 14.624) < 1e-6
    True
    """

    def predict(self, x):
        """
        Predict the value of the dependent variable given a vector or
        an RDD of vectors containing values for the independent variables.
        """
        if isinstance(x, RDD):
            return x.map(self.predict)
        x = _convert_to_vector(x)
        return self.weights.dot(x) + self.intercept


@inherit_doc
class LinearRegressionModel(LinearRegressionModelBase):

    """A linear regression model derived from a least-squares fit.

    >>> from pyspark.mllib.regression import LabeledPoint
    >>> data = [
    ...     LabeledPoint(0.0, [0.0]),
    ...     LabeledPoint(1.0, [1.0]),
    ...     LabeledPoint(3.0, [2.0]),
    ...     LabeledPoint(2.0, [3.0])
    ... ]
    >>> lrm = LinearRegressionWithSGD.train(sc.parallelize(data), iterations=10,
    ...     initialWeights=np.array([1.0]))
    >>> abs(lrm.predict(np.array([0.0])) - 0) < 0.5
    True
    >>> abs(lrm.predict(np.array([1.0])) - 1) < 0.5
    True
    >>> abs(lrm.predict(SparseVector(1, {0: 1.0})) - 1) < 0.5
    True
    >>> abs(lrm.predict(sc.parallelize([[1.0]])).collect()[0] - 1) < 0.5
    True
    >>> import os, tempfile
    >>> path = tempfile.mkdtemp()
    >>> lrm.save(sc, path)
    >>> sameModel = LinearRegressionModel.load(sc, path)
    >>> abs(sameModel.predict(np.array([0.0])) - 0) < 0.5
    True
    >>> abs(sameModel.predict(np.array([1.0])) - 1) < 0.5
    True
    >>> abs(sameModel.predict(SparseVector(1, {0: 1.0})) - 1) < 0.5
    True
    >>> from shutil import rmtree
    >>> try:
    ...     rmtree(path)
    ... except:
    ...     pass
    >>> data = [
    ...     LabeledPoint(0.0, SparseVector(1, {0: 0.0})),
    ...     LabeledPoint(1.0, SparseVector(1, {0: 1.0})),
    ...     LabeledPoint(3.0, SparseVector(1, {0: 2.0})),
    ...     LabeledPoint(2.0, SparseVector(1, {0: 3.0}))
    ... ]
    >>> lrm = LinearRegressionWithSGD.train(sc.parallelize(data), iterations=10,
    ...     initialWeights=array([1.0]))
    >>> abs(lrm.predict(array([0.0])) - 0) < 0.5
    True
    >>> abs(lrm.predict(SparseVector(1, {0: 1.0})) - 1) < 0.5
    True
    >>> lrm = LinearRegressionWithSGD.train(sc.parallelize(data), iterations=10, step=1.0,
    ...    miniBatchFraction=1.0, initialWeights=array([1.0]), regParam=0.1, regType="l2",
    ...    intercept=True, validateData=True)
    >>> abs(lrm.predict(array([0.0])) - 0) < 0.5
    True
    >>> abs(lrm.predict(SparseVector(1, {0: 1.0})) - 1) < 0.5
    True
    """
    def save(self, sc, path):
        java_model = sc._jvm.org.apache.spark.mllib.regression.LinearRegressionModel(
            _py2java(sc, self._coeff), self.intercept)
        java_model.save(sc._jsc.sc(), path)

    @classmethod
    def load(cls, sc, path):
        java_model = sc._jvm.org.apache.spark.mllib.regression.LinearRegressionModel.load(
            sc._jsc.sc(), path)
        weights = _java2py(sc, java_model.weights())
        intercept = java_model.intercept()
        model = LinearRegressionModel(weights, intercept)
        return model


# train_func should take two parameters, namely data and initial_weights, and
# return the result of a call to the appropriate JVM stub.
# _regression_train_wrapper is responsible for setup and error checking.
def _regression_train_wrapper(train_func, modelClass, data, initial_weights):
    from pyspark.mllib.classification import LogisticRegressionModel
    first = data.first()
    if not isinstance(first, LabeledPoint):
        raise TypeError("data should be an RDD of LabeledPoint, but got %s" % type(first))
    if initial_weights is None:
        initial_weights = [0.0] * len(data.first().features)
    if (modelClass == LogisticRegressionModel):
        weights, intercept, numFeatures, numClasses = train_func(
            data, _convert_to_vector(initial_weights))
        return modelClass(weights, intercept, numFeatures, numClasses)
    else:
        weights, intercept = train_func(data, _convert_to_vector(initial_weights))
        return modelClass(weights, intercept)


class LinearRegressionWithSGD(object):

    @classmethod
    def train(cls, data, iterations=100, step=1.0, miniBatchFraction=1.0,
              initialWeights=None, regParam=0.0, regType=None, intercept=False,
              validateData=True):
        """
        Train a linear regression model using Stochastic Gradient
        Descent (SGD).
        This solves the least squares regression formulation

            f(weights) = 1/(2n) ||A weights - y||^2,

        which is the mean squared error.
        Here the data matrix has n rows, and the input RDD holds the
        set of rows of A, each with its corresponding right hand side
        label y. See also the documentation for the precise formulation.

        :param data:              The training data, an RDD of
                                  LabeledPoint.
        :param iterations:        The number of iterations
                                  (default: 100).
        :param step:              The step parameter used in SGD
                                  (default: 1.0).
        :param miniBatchFraction: Fraction of data to be used for each
                                  SGD iteration (default: 1.0).
        :param initialWeights:    The initial weights (default: None).
        :param regParam:          The regularizer parameter
                                  (default: 0.0).
        :param regType:           The type of regularizer used for
                                  training our model.

                                  :Allowed values:
                                     - "l1" for using L1 regularization (lasso),
                                     - "l2" for using L2 regularization (ridge),
                                     - None for no regularization

                                     (default: None)

        :param intercept:         Boolean parameter which indicates the
                                  use or not of the augmented representation
                                  for training data (i.e. whether bias
                                  features are activated or not,
                                  default: False).
        :param validateData:      Boolean parameter which indicates if
                                  the algorithm should validate data
                                  before training. (default: True)
        """
        def train(rdd, i):
            return callMLlibFunc("trainLinearRegressionModelWithSGD", rdd, int(iterations),
                                 float(step), float(miniBatchFraction), i, float(regParam),
                                 regType, bool(intercept), bool(validateData))

        return _regression_train_wrapper(train, LinearRegressionModel, data, initialWeights)


@inherit_doc
class LassoModel(LinearRegressionModelBase):

    """A linear regression model derived from a least-squares fit with
    an l_1 penalty term.

    >>> from pyspark.mllib.regression import LabeledPoint
    >>> data = [
    ...     LabeledPoint(0.0, [0.0]),
    ...     LabeledPoint(1.0, [1.0]),
    ...     LabeledPoint(3.0, [2.0]),
    ...     LabeledPoint(2.0, [3.0])
    ... ]
    >>> lrm = LassoWithSGD.train(sc.parallelize(data), iterations=10, initialWeights=array([1.0]))
    >>> abs(lrm.predict(np.array([0.0])) - 0) < 0.5
    True
    >>> abs(lrm.predict(np.array([1.0])) - 1) < 0.5
    True
    >>> abs(lrm.predict(SparseVector(1, {0: 1.0})) - 1) < 0.5
    True
    >>> abs(lrm.predict(sc.parallelize([[1.0]])).collect()[0] - 1) < 0.5
    True
    >>> import os, tempfile
    >>> path = tempfile.mkdtemp()
    >>> lrm.save(sc, path)
    >>> sameModel = LassoModel.load(sc, path)
    >>> abs(sameModel.predict(np.array([0.0])) - 0) < 0.5
    True
    >>> abs(sameModel.predict(np.array([1.0])) - 1) < 0.5
    True
    >>> abs(sameModel.predict(SparseVector(1, {0: 1.0})) - 1) < 0.5
    True
    >>> from shutil import rmtree
    >>> try:
    ...    rmtree(path)
    ... except:
    ...    pass
    >>> data = [
    ...     LabeledPoint(0.0, SparseVector(1, {0: 0.0})),
    ...     LabeledPoint(1.0, SparseVector(1, {0: 1.0})),
    ...     LabeledPoint(3.0, SparseVector(1, {0: 2.0})),
    ...     LabeledPoint(2.0, SparseVector(1, {0: 3.0}))
    ... ]
    >>> lrm = LinearRegressionWithSGD.train(sc.parallelize(data), iterations=10,
    ...     initialWeights=array([1.0]))
    >>> abs(lrm.predict(np.array([0.0])) - 0) < 0.5
    True
    >>> abs(lrm.predict(SparseVector(1, {0: 1.0})) - 1) < 0.5
    True
    >>> lrm = LassoWithSGD.train(sc.parallelize(data), iterations=10, step=1.0,
    ...     regParam=0.01, miniBatchFraction=1.0, initialWeights=array([1.0]), intercept=True,
    ...     validateData=True)
    >>> abs(lrm.predict(np.array([0.0])) - 0) < 0.5
    True
    >>> abs(lrm.predict(SparseVector(1, {0: 1.0})) - 1) < 0.5
    True
    """
    def save(self, sc, path):
        java_model = sc._jvm.org.apache.spark.mllib.regression.LassoModel(
            _py2java(sc, self._coeff), self.intercept)
        java_model.save(sc._jsc.sc(), path)

    @classmethod
    def load(cls, sc, path):
        java_model = sc._jvm.org.apache.spark.mllib.regression.LassoModel.load(
            sc._jsc.sc(), path)
        weights = _java2py(sc, java_model.weights())
        intercept = java_model.intercept()
        model = LassoModel(weights, intercept)
        return model


class LassoWithSGD(object):

    @classmethod
    def train(cls, data, iterations=100, step=1.0, regParam=0.01,
              miniBatchFraction=1.0, initialWeights=None, intercept=False,
              validateData=True):
        """
        Train a regression model with L1-regularization using
        Stochastic Gradient Descent.
        This solves the l1-regularized least squares regression
        formulation

            f(weights) = 1/(2n) ||A weights - y||^2  + regParam ||weights||_1.

        Here the data matrix has n rows, and the input RDD holds the
        set of rows of A, each with its corresponding right hand side
        label y. See also the documentation for the precise formulation.

        :param data:              The training data, an RDD of
                                  LabeledPoint.
        :param iterations:        The number of iterations
                                  (default: 100).
        :param step:              The step parameter used in SGD
                                  (default: 1.0).
        :param regParam:          The regularizer parameter
                                  (default: 0.01).
        :param miniBatchFraction: Fraction of data to be used for each
                                  SGD iteration (default: 1.0).
        :param initialWeights:    The initial weights (default: None).
        :param intercept:         Boolean parameter which indicates the
                                  use or not of the augmented representation
                                  for training data (i.e. whether bias
                                  features are activated or not,
                                  default: False).
        :param validateData:      Boolean parameter which indicates if
                                  the algorithm should validate data
                                  before training. (default: True)
        """
        def train(rdd, i):
            return callMLlibFunc("trainLassoModelWithSGD", rdd, int(iterations), float(step),
                                 float(regParam), float(miniBatchFraction), i, bool(intercept),
                                 bool(validateData))

        return _regression_train_wrapper(train, LassoModel, data, initialWeights)


@inherit_doc
class RidgeRegressionModel(LinearRegressionModelBase):

    """A linear regression model derived from a least-squares fit with
    an l_2 penalty term.

    >>> from pyspark.mllib.regression import LabeledPoint
    >>> data = [
    ...     LabeledPoint(0.0, [0.0]),
    ...     LabeledPoint(1.0, [1.0]),
    ...     LabeledPoint(3.0, [2.0]),
    ...     LabeledPoint(2.0, [3.0])
    ... ]
    >>> lrm = RidgeRegressionWithSGD.train(sc.parallelize(data), iterations=10,
    ...     initialWeights=array([1.0]))
    >>> abs(lrm.predict(np.array([0.0])) - 0) < 0.5
    True
    >>> abs(lrm.predict(np.array([1.0])) - 1) < 0.5
    True
    >>> abs(lrm.predict(SparseVector(1, {0: 1.0})) - 1) < 0.5
    True
    >>> abs(lrm.predict(sc.parallelize([[1.0]])).collect()[0] - 1) < 0.5
    True
    >>> import os, tempfile
    >>> path = tempfile.mkdtemp()
    >>> lrm.save(sc, path)
    >>> sameModel = RidgeRegressionModel.load(sc, path)
    >>> abs(sameModel.predict(np.array([0.0])) - 0) < 0.5
    True
    >>> abs(sameModel.predict(np.array([1.0])) - 1) < 0.5
    True
    >>> abs(sameModel.predict(SparseVector(1, {0: 1.0})) - 1) < 0.5
    True
    >>> from shutil import rmtree
    >>> try:
    ...    rmtree(path)
    ... except:
    ...    pass
    >>> data = [
    ...     LabeledPoint(0.0, SparseVector(1, {0: 0.0})),
    ...     LabeledPoint(1.0, SparseVector(1, {0: 1.0})),
    ...     LabeledPoint(3.0, SparseVector(1, {0: 2.0})),
    ...     LabeledPoint(2.0, SparseVector(1, {0: 3.0}))
    ... ]
    >>> lrm = LinearRegressionWithSGD.train(sc.parallelize(data), iterations=10,
    ...     initialWeights=array([1.0]))
    >>> abs(lrm.predict(np.array([0.0])) - 0) < 0.5
    True
    >>> abs(lrm.predict(SparseVector(1, {0: 1.0})) - 1) < 0.5
    True
    >>> lrm = RidgeRegressionWithSGD.train(sc.parallelize(data), iterations=10, step=1.0,
    ...     regParam=0.01, miniBatchFraction=1.0, initialWeights=array([1.0]), intercept=True,
    ...     validateData=True)
    >>> abs(lrm.predict(np.array([0.0])) - 0) < 0.5
    True
    >>> abs(lrm.predict(SparseVector(1, {0: 1.0})) - 1) < 0.5
    True
    """
    def save(self, sc, path):
        java_model = sc._jvm.org.apache.spark.mllib.regression.RidgeRegressionModel(
            _py2java(sc, self._coeff), self.intercept)
        java_model.save(sc._jsc.sc(), path)

    @classmethod
    def load(cls, sc, path):
        java_model = sc._jvm.org.apache.spark.mllib.regression.RidgeRegressionModel.load(
            sc._jsc.sc(), path)
        weights = _java2py(sc, java_model.weights())
        intercept = java_model.intercept()
        model = RidgeRegressionModel(weights, intercept)
        return model


class RidgeRegressionWithSGD(object):

    @classmethod
    def train(cls, data, iterations=100, step=1.0, regParam=0.01,
              miniBatchFraction=1.0, initialWeights=None, intercept=False,
              validateData=True):
        """
        Train a regression model with L2-regularization using
        Stochastic Gradient Descent.
        This solves the l2-regularized least squares regression
        formulation

            f(weights) = 1/(2n) ||A weights - y||^2 + regParam/2 ||weights||^2.

        Here the data matrix has n rows, and the input RDD holds the
        set of rows of A, each with its corresponding right hand side
        label y. See also the documentation for the precise formulation.

        :param data:              The training data, an RDD of
                                  LabeledPoint.
        :param iterations:        The number of iterations
                                  (default: 100).
        :param step:              The step parameter used in SGD
                                  (default: 1.0).
        :param regParam:          The regularizer parameter
                                  (default: 0.01).
        :param miniBatchFraction: Fraction of data to be used for each
                                  SGD iteration (default: 1.0).
        :param initialWeights:    The initial weights (default: None).
        :param intercept:         Boolean parameter which indicates the
                                  use or not of the augmented representation
                                  for training data (i.e. whether bias
                                  features are activated or not,
                                  default: False).
        :param validateData:      Boolean parameter which indicates if
                                  the algorithm should validate data
                                  before training. (default: True)
        """
        def train(rdd, i):
            return callMLlibFunc("trainRidgeModelWithSGD", rdd, int(iterations), float(step),
                                 float(regParam), float(miniBatchFraction), i, bool(intercept),
                                 bool(validateData))

        return _regression_train_wrapper(train, RidgeRegressionModel, data, initialWeights)


class IsotonicRegressionModel(Saveable, Loader):

    """
    Regression model for isotonic regression.

    :param boundaries: Array of boundaries for which predictions are
            known. Boundaries must be sorted in increasing order.
    :param predictions: Array of predictions associated to the
            boundaries at the same index. Results of isotonic
            regression and therefore monotone.
    :param isotonic: indicates whether this is isotonic or antitonic.

    >>> data = [(1, 0, 1), (2, 1, 1), (3, 2, 1), (1, 3, 1), (6, 4, 1), (17, 5, 1), (16, 6, 1)]
    >>> irm = IsotonicRegression.train(sc.parallelize(data))
    >>> irm.predict(3)
    2.0
    >>> irm.predict(5)
    16.5
    >>> irm.predict(sc.parallelize([3, 5])).collect()
    [2.0, 16.5]
    >>> import os, tempfile
    >>> path = tempfile.mkdtemp()
    >>> irm.save(sc, path)
    >>> sameModel = IsotonicRegressionModel.load(sc, path)
    >>> sameModel.predict(3)
    2.0
    >>> sameModel.predict(5)
    16.5
    >>> from shutil import rmtree
    >>> try:
    ...     rmtree(path)
    ... except OSError:
    ...     pass
    """

    def __init__(self, boundaries, predictions, isotonic):
        self.boundaries = boundaries
        self.predictions = predictions
        self.isotonic = isotonic

    def predict(self, x):
        """
        Predict labels for provided features.
        Using a piecewise linear function.
        1) If x exactly matches a boundary then associated prediction
        is returned. In case there are multiple predictions with the
        same boundary then one of them is returned. Which one is
        undefined (same as java.util.Arrays.binarySearch).
        2) If x is lower or higher than all boundaries then first or
        last prediction is returned respectively. In case there are
        multiple predictions with the same boundary then the lowest
        or highest is returned respectively.
        3) If x falls between two values in boundary array then
        prediction is treated as piecewise linear function and
        interpolated value is returned. In case there are multiple
        values with the same boundary then the same rules as in 2)
        are used.

        :param x: Feature or RDD of Features to be labeled.
        """
        if isinstance(x, RDD):
            return x.map(lambda v: self.predict(v))
        return np.interp(x, self.boundaries, self.predictions)

    def save(self, sc, path):
        java_boundaries = _py2java(sc, self.boundaries.tolist())
        java_predictions = _py2java(sc, self.predictions.tolist())
        java_model = sc._jvm.org.apache.spark.mllib.regression.IsotonicRegressionModel(
            java_boundaries, java_predictions, self.isotonic)
        java_model.save(sc._jsc.sc(), path)

    @classmethod
    def load(cls, sc, path):
        java_model = sc._jvm.org.apache.spark.mllib.regression.IsotonicRegressionModel.load(
            sc._jsc.sc(), path)
        py_boundaries = _java2py(sc, java_model.boundaryVector()).toArray()
        py_predictions = _java2py(sc, java_model.predictionVector()).toArray()
        return IsotonicRegressionModel(py_boundaries, py_predictions, java_model.isotonic)


class IsotonicRegression(object):

    @classmethod
    def train(cls, data, isotonic=True):
        """
        Train a isotonic regression model on the given data.

        :param data: RDD of (label, feature, weight) tuples.
        :param isotonic: Whether this is isotonic or antitonic.
        """
        boundaries, predictions = callMLlibFunc("trainIsotonicRegressionModel",
                                                data.map(_convert_to_vector), bool(isotonic))
        return IsotonicRegressionModel(boundaries.toArray(), predictions.toArray(), isotonic)


class StreamingLinearAlgorithm(object):
    """
    Base class that has to be inherited by any StreamingLinearAlgorithm.

    Prevents reimplementation of methods predictOn and predictOnValues.
    """
    def __init__(self, model):
        self._model = model

    def latestModel(self):
        """
        Returns the latest model.
        """
        return self._model

    def _validate(self, dstream):
        if not isinstance(dstream, DStream):
            raise TypeError(
                "dstream should be a DStream object, got %s" % type(dstream))
        if not self._model:
            raise ValueError(
                "Model must be intialized using setInitialWeights")

    def predictOn(self, dstream):
        """
        Make predictions on a dstream.

        :return: Transformed dstream object.
        """
        self._validate(dstream)
        return dstream.map(lambda x: self._model.predict(x))

    def predictOnValues(self, dstream):
        """
        Make predictions on a keyed dstream.

        :return: Transformed dstream object.
        """
        self._validate(dstream)
        return dstream.mapValues(lambda x: self._model.predict(x))


@inherit_doc
class StreamingLinearRegressionWithSGD(StreamingLinearAlgorithm):
    """
    Run LinearRegression with SGD on a batch of data.

    The problem minimized is (1 / n_samples) * (y - weights'X)**2.
    After training on a batch of data, the weights obtained at the end of
    training are used as initial weights for the next batch.

    :param: stepSize Step size for each iteration of gradient descent.
    :param: numIterations Total number of iterations run.
    :param: miniBatchFraction Fraction of data on which SGD is run for each
                              iteration.
    """
    def __init__(self, stepSize=0.1, numIterations=50, miniBatchFraction=1.0):
        self.stepSize = stepSize
        self.numIterations = numIterations
        self.miniBatchFraction = miniBatchFraction
        self._model = None
        super(StreamingLinearRegressionWithSGD, self).__init__(
            model=self._model)

    def setInitialWeights(self, initialWeights):
        """
        Set the initial value of weights.

        This must be set before running trainOn and predictOn
        """
        initialWeights = _convert_to_vector(initialWeights)
        self._model = LinearRegressionModel(initialWeights, 0)
        return self

    def trainOn(self, dstream):
        """Train the model on the incoming dstream."""
        self._validate(dstream)

        def update(rdd):
            # LinearRegressionWithSGD.train raises an error for an empty RDD.
            if not rdd.isEmpty():
                self._model = LinearRegressionWithSGD.train(
                    rdd, self.numIterations, self.stepSize,
                    self.miniBatchFraction, self._model.weights,
                    intercept=self._model.intercept, convergenceTol=self.convergenceTol)

        dstream.foreachRDD(update)


def _test():
    import doctest
    from pyspark import SparkContext
    import pyspark.mllib.regression
    globs = pyspark.mllib.regression.__dict__.copy()
    globs['sc'] = SparkContext('local[2]', 'PythonTest', batchSize=2)
    (failure_count, test_count) = doctest.testmod(globs=globs, optionflags=doctest.ELLIPSIS)
    globs['sc'].stop()
    if failure_count:
        exit(-1)

if __name__ == "__main__":
    _test()
