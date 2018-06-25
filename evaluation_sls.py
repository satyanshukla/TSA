"""
    Evaluation module for streaming least squares algorithm in terms of mean average precision.
"""

import numpy as np
import pandas as pd

from AnomalyDetection import detect_anomalies

def label_anomaly_windows(label):
    """
    Converts the point wise anomaly labels to windows for intersection over union calculation.
    :param labels (type: panda series): input labels 1/0 for each point
    :return (type: list): set of intervals of anomaly (start time, end time)
    """
    labels = label.values
    timestamps = label.index
    labeled_anomaly_window = []
    start = 0
    #if the anomaly window starts from the beginning
    for i in range(1, len(label)):
        if labels[i] == 1 and labels[i-1] == 0:
            start = timestamps[i]
        elif labels[i-1] == 1 and labels[i] == 0:
            end = timestamps[i-1]
            labeled_anomaly_window.append((start, end))
        elif i == len(labels)-1 and labels[i] == 1:
            #if the anomaly window extends till the end
            labeled_anomaly_window.append((start, i))

    return labeled_anomaly_window


def calculate_IOU(anomalies, label_window):
    """
    Calculates Intersection over Union (IoU) for anomalous windows detected by the algorithm. Since a single window can contain multiple       
    true anomalous windows, anomaly_region keeps track of how many true windows each detected window intersects. This information is           
    required in the calculation of recall.
    :param anomalies (panda dataframe): anomaly windows generated by the algorithm
    :param label_window (type: list):  true anomalous windows on the data, each item is a tuple with start and end index
    :return iou (type: list): intersection over union if the anomaly windows overlap with actual labels else 0
    :return anomaly_region (type: list): list of labels associated with each anomaly window since there could be multiple
    """
    
    iou = []
    anomaly_region = []
    from datetime import datetime
    def stt(s): return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    def t_max(t1, t2): return t1 if t1 > t2 else t2
    def t_min(t1, t2): return t1 if t1 < t2 else t2
        
    
    #IoU calculation for each anomaly window intersection with all other true windows
    for i in range(len(anomalies)):
        iou_i = 0
        region = []
        start = stt(anomalies.start[i])
        end = stt(anomalies.end[i])
        for j in range(len(label_window)):

            if start <= label_window[j][0] and end >= label_window[j][0]:
                overlap = 1 + (t_min(label_window[j][1], end) - label_window[j][0]).total_seconds()/60 
                union   = 1 + (t_max(label_window[j][1], end)- start).total_seconds()/60 
                iou_i += (float(overlap)/union)
                region.append(j)

            elif start >= label_window[j][0] and end <= label_window[j][1]:
                overlap = 1 + (end - start).total_seconds()/60 
                union   = 1 + (label_window[j][1]- label_window[j][0]).total_seconds()/60 
                iou_i += (float(overlap)/union)
                region.append(j)
                
            elif start <= label_window[j][1] and end >= label_window[j][1]:
                overlap = 1 + (label_window[j][1] - start).total_seconds()/60 
                union   = 1 + (end - label_window[j][0]).total_seconds()/60 
                iou_i += (float(overlap)/union)
                region.append(j)
                
        anomaly_region.append(region)
        iou.append(iou_i)  
    
    return iou, anomaly_region

def average_precision_sls(anomalies, label, iou_threshold):
    """
    Calculates average precision which summarises the shape of the precision/recall curve, and is defined as the mean precision at a set of
    eleven equally spaced recall levels. The precision at each recall level r is interpolated by taking the maximum precision measured for     
    corresponding recalls exceeding r. 
    Reference: http://homepages.inf.ed.ac.uk/ckiw/postscript/ijcv_voc09.pdf
    :param anomalies (panda dataframe): anomaly windows generated by the algorithm (sorted in descending scores of the anomaly scores)
    :param label (type: panda series): input labels 1/0 for each point
    :param iou_threshold (type: float): threshold above which regions are considered correct detection
    :return (type: float) : AP_score (average precision)
    """
    labeled_data = label_anomaly_windows(label)
    
    iou, anomaly_region = calculate_IOU(anomalies, labeled_data)
    
    precision = []
    recall = []

    for i in range(1, len(iou)):
        #selecting top i anomaly scores and predicting them as positive label
        iou_i = iou[:i]
        region = []
        tp, fp, fn = 0,0,0
        for j in range(len(iou_i)):
            if iou_i[j] > iou_threshold:
                tp += 1
                for window in anomaly_region[j]:
                    if window not in region:
                        region.append(window)
        fp = len(iou_i) - tp
                
        precision.append(float(tp)/ (tp + fp))
        recall.append(len(region)/ len(labeled_data))
    
    #Recall values for calculating average precision
    recall_interp = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    recall_interp = recall_interp[::-1]
    recall = recall[::-1]
    precision = precision[::-1]
    precision_interp = []
    for val in recall_interp:
        k = 0
        p = 0
        while k < len(recall) and recall[k] >= val :
            p = precision[k] if precision[k] >= p else p
            k += 1
            
        precision_interp.append(p)
    return np.mean(precision_interp)


def mean_average_precision_sls(data, labels, lag):
    """
    Mean Average Precision score is calculated by taking the mean of average precision over all IoU (intersection over union) thresholds.      
    Averaging over multiple IoU thresholds rather than only considering one generous threshold of IoU tends to reward models that are          
    better at precise localization.
    :param data (type: panda series): input time series data
    :param labels (type: panda series): input labels 1/0 for each point
    :param lag (type: int): lag time
    :return (type: float): mean average precision score over given intersection over union (IoU) thresholds 
    """
    anomalies, _ = detect_anomalies(data, lag, num_anomalies=len(data)/lag, visualize=False)
    #intersection over union thresholds for mean average precision calculation 
    thresholds = [0.05, 0.10, 0.15, 0.20, 0.25]
    mean = 0
    for i in range(len(thresholds)):
        mean += average_precision_sls(anomalies, labels, thresholds[i])
    return float(mean)/ len(thresholds)



















