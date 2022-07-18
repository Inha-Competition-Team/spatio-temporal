# -*-Encoding: utf-8 -*-
################################################################################
#
# Copyright (c) 2022 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
Description: Some useful metrics
Authors: Lu,Xinjiang (luxinjiang@baidu.com)
Date:    2022/03/10
"""
import time
import numpy as np
import tensorflow as tf

def ignore_zeros(predictions, grounds):
    """
    Desc:
        Ignore the zero values for evaluation
    Args:
        predictions:
        grounds:
    Returns:
        Predictions and ground truths
    """
    preds = predictions[np.where(grounds != 0)]
    gts = grounds[np.where(grounds != 0)]
    return preds, gts


def rse(pred, ground_truth):
    """
    Desc:
        Root square error
    Args:
        pred:
        ground_truth: ground truth vector
    Returns:
        RSE value
    """
    _rse = 0.
    if len(pred) > 0 and len(ground_truth) > 0:
        _rse = np.sqrt(np.sum((ground_truth - pred) ** 2)) / np.sqrt(np.sum((ground_truth - ground_truth.mean()) ** 2))
    return _rse


def corr(pred, gt):
    """
    Desc:
        Correlation between the prediction and ground truth
    Args:
        pred:
        gt: ground truth vector
    Returns:
        Correlation
    """
    _corr = 0.
    if len(pred) > 0 and len(gt) > 0:
        u = ((gt - gt.mean(0)) * (pred - pred.mean(0))).sum(0)
        d = np.sqrt(((gt - gt.mean(0)) ** 2 * (pred - pred.mean(0)) ** 2).sum(0))
        _corr = (u / d).mean(-1)
    return _corr


def mae(pred, gt):
    """
    Desc:
        Mean Absolute Error
    Args:
        pred:
        gt: ground truth vector
    Returns:
        MAE value
    """
    _mae = 0.
    if len(pred) > 0 and len(gt) > 0:
        _mae = np.nanmean(np.abs(pred - gt))
    return _mae


def mse(pred, gt):
    """
    Desc:
        Mean Square Error
    Args:
        pred:
        gt: ground truth vector
    Returns:
        MSE value
    """
    _mse = 0.
    if len(pred) > 0 and len(gt) > 0:
        _mse = np.nanmean((pred - gt) ** 2)
    return _mse


def rmse(pred, gt):
    """
    Desc:
        Root Mean Square Error
    Args:
        pred:
        gt: ground truth vector
    Returns:
        RMSE value
    """
    return np.sqrt(mse(pred, gt))


def mape(pred, gt):
    """
    Desc:
        Mean Absolute Percentage Error
    Args:
        pred:
        gt: ground truth vector
    Returns:
        MAPE value
    """
    _mape = 0.
    if len(pred) > 0 and len(gt) > 0:
        _mape = np.mean(np.abs((pred - gt) / gt))
    return _mape


def mspe(pred, gt):
    """
    Desc:
        Mean Square Percentage Error
    Args:
        pred:
        gt: ground truth vector
    Returns:
        MSPE value
    """
    return np.mean(np.square((pred - gt) / gt)) if len(pred) > 0 and len(gt) > 0 else 0


def regressor_scores(prediction, gt):
    """
    Desc:
        Some common metrics for regression problems
    Args:
        prediction:
        gt: ground truth vector
    Returns:
        A tuple of metrics
    """
    _mae = mae(prediction, gt)
    _rmse = rmse(prediction, gt)
    return _mae, _rmse


def turbine_scores(pred, gt, raw_data, examine_len, stride=1):
    """
    Desc:
        Calculate the MAE and RMSE of one turbine
    Args:
        pred: prediction for one turbine
        gt: ground truth
        raw_data: the DataFrame of one wind turbine
        examine_len: 288 for 2days
        stride:
    Returns:
        The averaged MAE and RMSE
    """
    cond = (raw_data['Patv'] <= 0) & (raw_data['Wspd'] > 2.5) | \
           (raw_data['Pab1'] > 89) | (raw_data['Pab2'] > 89) | (raw_data['Pab3'] > 89) | \
           (raw_data['Wdir'] < -180) | (raw_data['Wdir'] > 180) | (raw_data['Ndir'] < -720) | (raw_data['Ndir'] > 720) | \
           (raw_data['Patv'].isnull())
    maes, rmses = [], []
    cnt_sample, out_seq_len, _ = pred.shape
    cnt_sample = out_seq_len
    for i in range(examine_len, cnt_sample+1, stride):
        # indices = np.where(~cond[i:out_seq_len + i])

        # roll window size from 288 to 0,
        # indices = np.where(~cond[i:])
        # abnormal_indices = np.where(cond[i:])
        # prediction = pred[0][i:]
        # targets = gt[0][i:]

        # roll window size from 0 to 288,
        indices = np.where(~cond[:i])
        abnormal_indices = np.where(cond[:i])
        prediction = pred[0][:i]
        targets = gt[0][:i]

        # drop all abnormal indices
        prediction = prediction[indices]
        targets = targets[indices]

        # not drop but error to 0
        # prediction[abnormal_indices] = 0
        # targets[abnormal_indices] = 0

        _mae, _rmse = regressor_scores(prediction[-examine_len:] , targets[-examine_len:])
        if _mae != _mae or _rmse != _rmse:
            continue
        maes.append(_mae)
        rmses.append(_rmse)
    avg_mae = np.array(maes).mean()
    avg_rmse = np.array(rmses).mean()
    return avg_mae, avg_rmse


def regressor_detailed_scores(predictions, gts, raw_df_lst):
    """
    Desc:
        Some common metrics for regression problems
    Args:
        predictions:
        gts: ground truth vector
        raw_df_lst:
        settings:
    Returns:
        A tuple of metrics
    """
    capacity = 134
    output_len = 288
    stride = 1
    # start_time = time.time()
    all_mae, all_rmse = [], []
    for i in range(capacity):
        prediction = predictions[i]
        gt = gts[i]
        raw_df = raw_df_lst[i]
        _mae, _rmse = turbine_scores(prediction, gt, raw_df, output_len, stride)
        # if settings["is_debug"]:
        #     end_time = time.time()
        #     print("\nSpent time for evaluating the {}-th turbine is {} secs\n".format(i, end_time - start_time))
        #     start_time = end_time

        all_mae.append(_mae)
        all_rmse.append(_rmse)
    total_mae = np.array(all_mae).sum()/capacity
    total_rmse = np.array(all_rmse).sum()/capacity
    return total_mae, total_rmse


def regressor_metrics(pred, gt):
    """
    Desc:
        Some common metrics for regression problems
    Args:
        pred:
        gt: ground truth vector
    Returns:
        A tuple of metrics
    """
    _mae = mae(pred, gt)
    _mse = mse(pred, gt)
    _rmse = rmse(pred, gt)
    # pred, gt = ignore_zeros(pred, gt)
    _mape = mape(pred, gt)
    _mspe = mspe(pred, gt)
    return _mae, _mse, _rmse, _mape, _mspe


class CondLoss(tf.keras.losses.Loss):
    def __init__(self, loss_fn, marked_target_value, **kwargs):
        self.loss_fn = loss_fn
        self.marked_target_value = marked_target_value
        super().__init__(**kwargs)
    def call(self, y_true, y_pred):
        # y_true, y_pred: [B, S, D]
        assert y_true.shape == y_pred.shape, f'Shape mismatch for output and ground truth array {y_true.shape} and {y_pred.shape}'

        _, S, D = y_true.shape  # Batch, Sequence, Dim of features
        y_true = tf.reshape(y_true, (-1, D))
        y_pred = tf.reshape(y_pred, (-1, D))

        idxs_valid_mark = (y_true[:, -1] != self.marked_target_value)  # [-1]: Patv
        y_true_valid, y_pred_valid = y_true[idxs_valid_mark], y_pred[idxs_valid_mark]
        res = y_true_valid - y_pred_valid

        if self.loss_fn == 'rmse':
            return tf.sqrt(tf.reduce_mean(tf.square(res)))
        elif self.loss_fn == 'mse':
            return tf.reduce_mean(tf.square(res))
        elif self.loss_fn == 'mae':
            return tf.reduce_mean(tf.abs(res))
        else:
            raise NotImplementedError
