# Copyright 2018 The TensorFlow Probability Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""Tests for MultivariateNormal."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Dependency imports
import numpy as np
from scipy import stats
import tensorflow as tf
import tensorflow_probability as tfp
from tensorflow.python.platform import tf_logging as logging


tfd = tfp.distributions


class MultivariateNormalTriLTest(tf.test.TestCase):

  def setUp(self):
    self._rng = np.random.RandomState(42)

  def _random_chol(self, *shape):
    mat = self._rng.rand(*shape)
    chol = tfd.matrix_diag_transform(mat, transform=tf.nn.softplus)
    chol = tf.matrix_band_part(chol, -1, 0)
    sigma = tf.matmul(chol, chol, adjoint_b=True)
    return self.evaluate(chol), self.evaluate(sigma)

  def testLogPDFScalarBatch(self):
    mu = self._rng.rand(2)
    chol, sigma = self._random_chol(2, 2)
    chol[1, 1] = -chol[1, 1]
    mvn = tfd.MultivariateNormalTriL(mu, chol, validate_args=True)
    x = self._rng.rand(2)

    log_pdf = mvn.log_prob(x)
    pdf = mvn.prob(x)

    scipy_mvn = stats.multivariate_normal(mean=mu, cov=sigma)

    expected_log_pdf = scipy_mvn.logpdf(x)
    expected_pdf = scipy_mvn.pdf(x)
    self.assertEqual((), log_pdf.get_shape())
    self.assertEqual((), pdf.get_shape())
    self.assertAllClose(expected_log_pdf, self.evaluate(log_pdf))
    self.assertAllClose(expected_pdf, self.evaluate(pdf))

  def testLogPDFXIsHigherRank(self):
    mu = self._rng.rand(2)
    chol, sigma = self._random_chol(2, 2)
    chol[0, 0] = -chol[0, 0]
    mvn = tfd.MultivariateNormalTriL(mu, chol, validate_args=True)
    x = self._rng.rand(3, 2)

    log_pdf = mvn.log_prob(x)
    pdf = mvn.prob(x)

    scipy_mvn = stats.multivariate_normal(mean=mu, cov=sigma)

    expected_log_pdf = scipy_mvn.logpdf(x)
    expected_pdf = scipy_mvn.pdf(x)
    self.assertEqual((3,), log_pdf.get_shape())
    self.assertEqual((3,), pdf.get_shape())
    self.assertAllClose(
        expected_log_pdf, self.evaluate(log_pdf), atol=0., rtol=0.02)
    self.assertAllClose(expected_pdf, self.evaluate(pdf), atol=0., rtol=0.03)

  def testLogPDFXLowerDimension(self):
    mu = self._rng.rand(3, 2)
    chol, sigma = self._random_chol(3, 2, 2)
    chol[0, 0, 0] = -chol[0, 0, 0]
    chol[2, 1, 1] = -chol[2, 1, 1]
    mvn = tfd.MultivariateNormalTriL(mu, chol, validate_args=True)
    x = self._rng.rand(2)

    log_pdf = mvn.log_prob(x)
    pdf = mvn.prob(x)

    self.assertEqual((3,), log_pdf.get_shape())
    self.assertEqual((3,), pdf.get_shape())

    # scipy can't do batches, so just test one of them.
    scipy_mvn = stats.multivariate_normal(mean=mu[1, :], cov=sigma[1, :, :])
    expected_log_pdf = scipy_mvn.logpdf(x)
    expected_pdf = scipy_mvn.pdf(x)

    self.assertAllClose(expected_log_pdf, self.evaluate(log_pdf)[1])
    self.assertAllClose(expected_pdf, self.evaluate(pdf)[1])

  def testEntropy(self):
    mu = self._rng.rand(2)
    chol, sigma = self._random_chol(2, 2)
    chol[0, 0] = -chol[0, 0]
    mvn = tfd.MultivariateNormalTriL(mu, chol, validate_args=True)
    entropy = mvn.entropy()

    scipy_mvn = stats.multivariate_normal(mean=mu, cov=sigma)
    expected_entropy = scipy_mvn.entropy()
    self.assertEqual(entropy.get_shape(), ())
    self.assertAllClose(expected_entropy, self.evaluate(entropy))

  def testEntropyMultidimensional(self):
    mu = self._rng.rand(3, 5, 2)
    chol, sigma = self._random_chol(3, 5, 2, 2)
    chol[1, 0, 0, 0] = -chol[1, 0, 0, 0]
    chol[2, 3, 1, 1] = -chol[2, 3, 1, 1]
    mvn = tfd.MultivariateNormalTriL(mu, chol, validate_args=True)
    entropy = mvn.entropy()

    # Scipy doesn't do batches, so test one of them.
    expected_entropy = stats.multivariate_normal(
        mean=mu[1, 1, :], cov=sigma[1, 1, :, :]).entropy()
    self.assertEqual(entropy.get_shape(), (3, 5))
    self.assertAllClose(expected_entropy, self.evaluate(entropy)[1, 1])

  def testSample(self):
    mu = self._rng.rand(2)
    chol, sigma = self._random_chol(2, 2)
    chol[0, 0] = -chol[0, 0]
    sigma[0, 1] = -sigma[0, 1]
    sigma[1, 0] = -sigma[1, 0]

    n = tf.constant(100000)
    mvn = tfd.MultivariateNormalTriL(mu, chol, validate_args=True)
    samples = mvn.sample(n, seed=137)
    sample_values = self.evaluate(samples)
    self.assertEqual(samples.get_shape(), [int(100e3), 2])
    self.assertAllClose(sample_values.mean(axis=0), mu, atol=1e-2)
    self.assertAllClose(np.cov(sample_values, rowvar=0), sigma, atol=0.06)

  def testSingularScaleRaises(self):
    mu = None
    chol = [[1., 0.], [0., 0.]]
    mvn = tfd.MultivariateNormalTriL(mu, chol, validate_args=True)
    with self.assertRaisesOpError("Singular operator"):
      self.evaluate(mvn.sample())

  def testSampleWithSampleShape(self):
    mu = self._rng.rand(3, 5, 2)
    chol, sigma = self._random_chol(3, 5, 2, 2)
    chol[1, 0, 0, 0] = -chol[1, 0, 0, 0]
    chol[2, 3, 1, 1] = -chol[2, 3, 1, 1]

    mvn = tfd.MultivariateNormalTriL(mu, chol, validate_args=True)
    samples_val = self.evaluate(mvn.sample((10, 11, 12), seed=137))

    # Check sample shape
    self.assertEqual((10, 11, 12, 3, 5, 2), samples_val.shape)

    # Check sample means
    x = samples_val[:, :, :, 1, 1, :]
    self.assertAllClose(
        x.reshape(10 * 11 * 12, 2).mean(axis=0), mu[1, 1], atol=0.05)

    # Check that log_prob(samples) works
    log_prob_val = self.evaluate(mvn.log_prob(samples_val))
    x_log_pdf = log_prob_val[:, :, :, 1, 1]
    expected_log_pdf = stats.multivariate_normal(
        mean=mu[1, 1, :], cov=sigma[1, 1, :, :]).logpdf(x)
    self.assertAllClose(expected_log_pdf, x_log_pdf)

  def testSampleMultiDimensional(self):
    mu = self._rng.rand(3, 5, 2)
    chol, sigma = self._random_chol(3, 5, 2, 2)
    chol[1, 0, 0, 0] = -chol[1, 0, 0, 0]
    chol[2, 3, 1, 1] = -chol[2, 3, 1, 1]

    mvn = tfd.MultivariateNormalTriL(mu, chol, validate_args=True)
    n = tf.constant(100000)
    samples = mvn.sample(n, seed=137)
    sample_values = self.evaluate(samples)

    self.assertEqual(samples.get_shape(), (100000, 3, 5, 2))
    self.assertAllClose(
        sample_values[:, 1, 1, :].mean(axis=0), mu[1, 1, :], atol=0.05)
    self.assertAllClose(
        np.cov(sample_values[:, 1, 1, :], rowvar=0),
        sigma[1, 1, :, :],
        atol=1e-1)

  def testShapes(self):
    mu = self._rng.rand(3, 5, 2)
    chol, _ = self._random_chol(3, 5, 2, 2)
    chol[1, 0, 0, 0] = -chol[1, 0, 0, 0]
    chol[2, 3, 1, 1] = -chol[2, 3, 1, 1]

    mvn = tfd.MultivariateNormalTriL(mu, chol, validate_args=True)

    # Shapes known at graph construction time.
    self.assertEqual((2,), tuple(mvn.event_shape.as_list()))
    self.assertEqual((3, 5), tuple(mvn.batch_shape.as_list()))

    # Shapes known at runtime.
    self.assertEqual((2,), tuple(self.evaluate(mvn.event_shape_tensor())))
    self.assertEqual((3, 5), tuple(self.evaluate(mvn.batch_shape_tensor())))

  def _random_mu_and_sigma(self, batch_shape, event_shape):
    # This ensures sigma is positive def.
    mat_shape = batch_shape + event_shape + event_shape
    mat = self._rng.randn(*mat_shape)
    perm = np.arange(mat.ndim)
    perm[-2:] = [perm[-1], perm[-2]]
    sigma = np.matmul(mat, np.transpose(mat, perm))

    mu_shape = batch_shape + event_shape
    mu = self._rng.randn(*mu_shape)

    return mu, sigma

  def testKLNonBatch(self):
    batch_shape = []
    event_shape = [2]
    mu_a, sigma_a = self._random_mu_and_sigma(batch_shape, event_shape)
    mu_b, sigma_b = self._random_mu_and_sigma(batch_shape, event_shape)
    mvn_a = tfd.MultivariateNormalTriL(
        loc=mu_a, scale_tril=np.linalg.cholesky(sigma_a), validate_args=True)
    mvn_b = tfd.MultivariateNormalTriL(
        loc=mu_b, scale_tril=np.linalg.cholesky(sigma_b), validate_args=True)

    kl = tfd.kl_divergence(mvn_a, mvn_b)
    self.assertEqual(batch_shape, kl.get_shape())

    kl_v = self.evaluate(kl)
    expected_kl = _compute_non_batch_kl(mu_a, sigma_a, mu_b, sigma_b)
    self.assertAllClose(expected_kl, kl_v)

  def testKLBatch(self):
    batch_shape = [2]
    event_shape = [3]
    mu_a, sigma_a = self._random_mu_and_sigma(batch_shape, event_shape)
    mu_b, sigma_b = self._random_mu_and_sigma(batch_shape, event_shape)
    mvn_a = tfd.MultivariateNormalTriL(
        loc=mu_a, scale_tril=np.linalg.cholesky(sigma_a), validate_args=True)
    mvn_b = tfd.MultivariateNormalTriL(
        loc=mu_b, scale_tril=np.linalg.cholesky(sigma_b), validate_args=True)

    kl = tfd.kl_divergence(mvn_a, mvn_b)
    self.assertEqual(batch_shape, kl.get_shape())

    kl_v = self.evaluate(kl)
    expected_kl_0 = _compute_non_batch_kl(mu_a[0, :], sigma_a[0, :, :],
                                          mu_b[0, :], sigma_b[0, :])
    expected_kl_1 = _compute_non_batch_kl(mu_a[1, :], sigma_a[1, :, :],
                                          mu_b[1, :], sigma_b[1, :])
    self.assertAllClose(expected_kl_0, kl_v[0])
    self.assertAllClose(expected_kl_1, kl_v[1])

  def testKLBatchBroadcast(self):
    batch_shape = [2]
    event_shape = [3]
    mu_a, sigma_a = self._random_mu_and_sigma(batch_shape, event_shape)
    # No batch shape.
    mu_b, sigma_b = self._random_mu_and_sigma([], event_shape)
    mvn_a = tfd.MultivariateNormalTriL(
        loc=mu_a, scale_tril=np.linalg.cholesky(sigma_a), validate_args=True)
    mvn_b = tfd.MultivariateNormalTriL(
        loc=mu_b, scale_tril=np.linalg.cholesky(sigma_b), validate_args=True)

    kl = tfd.kl_divergence(mvn_a, mvn_b)
    self.assertEqual(batch_shape, kl.get_shape())

    kl_v = self.evaluate(kl)
    expected_kl_0 = _compute_non_batch_kl(mu_a[0, :], sigma_a[0, :, :], mu_b,
                                          sigma_b)
    expected_kl_1 = _compute_non_batch_kl(mu_a[1, :], sigma_a[1, :, :], mu_b,
                                          sigma_b)
    self.assertAllClose(expected_kl_0, kl_v[0])
    self.assertAllClose(expected_kl_1, kl_v[1])

  def testKLTwoIdenticalDistributionsIsZero(self):
    batch_shape = [2]
    event_shape = [3]
    mu_a, sigma_a = self._random_mu_and_sigma(batch_shape, event_shape)
    mvn_a = tfd.MultivariateNormalTriL(
        loc=mu_a, scale_tril=np.linalg.cholesky(sigma_a), validate_args=True)

    # Should be zero since KL(p || p) = =.
    kl = tfd.kl_divergence(mvn_a, mvn_a)
    self.assertEqual(batch_shape, kl.get_shape())

    kl_v = self.evaluate(kl)
    self.assertAllClose(np.zeros(*batch_shape), kl_v)

  def testSampleLarge(self):
    mu = np.array([-1., 1], dtype=np.float32)
    scale_tril = np.array([[3., 0], [1, -2]], dtype=np.float32) / 3.

    true_mean = mu
    true_scale = scale_tril
    true_covariance = np.matmul(true_scale, true_scale.T)
    true_variance = np.diag(true_covariance)
    true_stddev = np.sqrt(true_variance)

    dist = tfd.MultivariateNormalTriL(
        loc=mu, scale_tril=scale_tril, validate_args=True)

    # The following distributions will test the KL divergence calculation.
    mvn_chol = tfd.MultivariateNormalTriL(
        loc=np.array([0.5, 1.2], dtype=np.float32),
        scale_tril=np.array([[3., 0], [1, 2]], dtype=np.float32),
        validate_args=True)

    n = int(10e3)
    samps = dist.sample(n, seed=0)
    sample_mean = tf.reduce_mean(samps, 0)
    x = samps - sample_mean
    sample_covariance = tf.matmul(x, x, transpose_a=True) / n

    sample_kl_chol = tf.reduce_mean(
        dist.log_prob(samps) - mvn_chol.log_prob(samps), 0)
    analytical_kl_chol = tfd.kl_divergence(dist, mvn_chol)

    scale = dist.scale.to_dense()

    [
        sample_mean_,
        analytical_mean_,
        sample_covariance_,
        analytical_covariance_,
        analytical_variance_,
        analytical_stddev_,
        sample_kl_chol_,
        analytical_kl_chol_,
        scale_,
    ] = self.evaluate([
        sample_mean,
        dist.mean(),
        sample_covariance,
        dist.covariance(),
        dist.variance(),
        dist.stddev(),
        sample_kl_chol,
        analytical_kl_chol,
        scale,
    ])

    sample_variance_ = np.diag(sample_covariance_)
    sample_stddev_ = np.sqrt(sample_variance_)

    logging.vlog(2, "true_mean:\n{}  ".format(true_mean))
    logging.vlog(2, "sample_mean:\n{}".format(sample_mean_))
    logging.vlog(2, "analytical_mean:\n{}".format(analytical_mean_))

    logging.vlog(2, "true_covariance:\n{}".format(true_covariance))
    logging.vlog(2, "sample_covariance:\n{}".format(sample_covariance_))
    logging.vlog(2, "analytical_covariance:\n{}".format(analytical_covariance_))

    logging.vlog(2, "true_variance:\n{}".format(true_variance))
    logging.vlog(2, "sample_variance:\n{}".format(sample_variance_))
    logging.vlog(2, "analytical_variance:\n{}".format(analytical_variance_))

    logging.vlog(2, "true_stddev:\n{}".format(true_stddev))
    logging.vlog(2, "sample_stddev:\n{}".format(sample_stddev_))
    logging.vlog(2, "analytical_stddev:\n{}".format(analytical_stddev_))

    logging.vlog(2, "true_scale:\n{}".format(true_scale))
    logging.vlog(2, "scale:\n{}".format(scale_))

    logging.vlog(
        2, "kl_chol:      analytical:{}  sample:{}".format(
            analytical_kl_chol_, sample_kl_chol_))

    self.assertAllClose(true_mean, sample_mean_, atol=0., rtol=0.03)
    self.assertAllClose(true_mean, analytical_mean_, atol=0., rtol=1e-6)

    self.assertAllClose(true_covariance, sample_covariance_, atol=0., rtol=0.03)
    self.assertAllClose(
        true_covariance, analytical_covariance_, atol=0., rtol=1e-6)

    self.assertAllClose(true_variance, sample_variance_, atol=0., rtol=0.02)
    self.assertAllClose(true_variance, analytical_variance_, atol=0., rtol=1e-6)

    self.assertAllClose(true_stddev, sample_stddev_, atol=0., rtol=0.01)
    self.assertAllClose(true_stddev, analytical_stddev_, atol=0., rtol=1e-6)

    self.assertAllClose(true_scale, scale_, atol=0., rtol=1e-6)

    self.assertAllClose(
        sample_kl_chol_, analytical_kl_chol_, atol=0., rtol=0.02)


def _compute_non_batch_kl(mu_a, sigma_a, mu_b, sigma_b):
  """Non-batch KL for N(mu_a, sigma_a), N(mu_b, sigma_b)."""
  # Check using numpy operations
  # This mostly repeats the tensorflow code _kl_mvn_mvn(), but in numpy.
  # So it is important to also check that KL(mvn, mvn) = 0.
  sigma_b_inv = np.linalg.inv(sigma_b)

  t = np.trace(sigma_b_inv.dot(sigma_a))
  q = (mu_b - mu_a).dot(sigma_b_inv).dot(mu_b - mu_a)
  k = mu_a.shape[0]
  l = np.log(np.linalg.det(sigma_b) / np.linalg.det(sigma_a))

  return 0.5 * (t + q - k + l)


if __name__ == "__main__":
  tf.test.main()
