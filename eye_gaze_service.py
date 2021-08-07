import random
from collections import Counter
import mediapipe as mp
import tensorflow as tf
import time
import numpy as np
import cv2
import json
import pygame
from service import Service, ListenerMixin
from reload_config_service import reload_config_service

# Use mouse positions in lieu of gaze
DEBUG = False

class EyeGazeService(Service, ListenerMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_config_service.register_listener(self)

    def setup(self):
        self.latest_areas = []
        config = json.load(open('./config.json', 'r'))
        self.frames_threshold_needed_for_click = config['frames_threshold_needed_for_click']
        self.thresholds = config['thresholds']
        self.positioning_samples = config['positioning_samples']
        self.eye_contour_indices = [
                33, 7, 7, 163, 163, 144, 144, 145, 145, 153, 153, 154, 154, 155,
                155, 133, 33, 246, 246, 161, 161, 160, 160, 159, 159, 158, 158,
                157, 157, 173, 173, 133]
        mp_iris = mp.solutions.iris
        self.iris = mp_iris.Iris()
        self.latest_center_positions = []
        self.current_area = (0, 0)
        self.last_image_received = None
        if DEBUG:
            self.mouse_pos = (0, 0)

    def get_relative_center_position_and_ear(self, iris_landmarks, eye_landmarks):
        center = iris_landmarks[0]
        eye_size_x = eye_landmarks[30][0] - eye_landmarks[0][0]
        eye_size_y = eye_landmarks[8][1] - eye_landmarks[24][1]
        relative_center_position = (
                (center[0] - eye_landmarks[0][0])/eye_size_x,
                (center[1] - eye_landmarks[0][1])/eye_size_y)
        return relative_center_position

    def get_gaze_area(self):
        if DEBUG:
            if self.mouse_pos[0] <= 1920*2/10:
                self.current_area = (-1, self.current_area[1])
            elif 1920*2/10 < self.mouse_pos[0] <= 1920*8/10:
                self.current_area = (0, self.current_area[1])
            elif self.mouse_pos[0] >= 1920*8/10:
                self.current_area = (1, self.current_area[1])

            if self.mouse_pos[1] < 1080*2/10:
                self.current_area = (self.current_area[0], -1)
            elif 1080*2/10 <= self.mouse_pos[1] <= 1080*8/10:
                self.current_area = (self.current_area[0], 0)
            elif self.mouse_pos[1] > 1080*8/10:
                self.current_area = (self.current_area[0], 1)

            self.latest_areas.append(self.current_area)
            if len(self.latest_areas) > self.frames_threshold_needed_for_click+5:
                self.latest_areas.pop(0)
            latest_areas_counts = Counter()
            for area in self.latest_areas:
                latest_areas_counts[area] += 1
            most_common = latest_areas_counts.most_common()
            clicked = any([x[1] > self.frames_threshold_needed_for_click for x in most_common])
            if clicked:
                self.latest_areas = []
                self.send_message_to_listeners({
                    'type': 'EYE_GAZE_CLICK',
                    'payload': {
                        'current_area': most_common[0][0]
                    }
                })

            progress_bars = {}
            # total_frames = sum([x[1] for x in most_common])
            total_frames = self.frames_threshold_needed_for_click
            last_most_common = progress_bars.copy()
            for area, frames in most_common:
                if clicked:
                    progress_bars[area] = 0
                else:
                    progress_bars[area] = frames/total_frames
            for area in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 0), (0, 1), (1, -1), (1, 0), (1, 1)]:
                if area in progress_bars.keys() and area != self.current_area:
                    progress_bars[area] -= 1/self.frames_threshold_needed_for_click*self.latest_areas.count(self.current_area)
            # for area, last_progress in last_most_common:
            #     if progress_bars[area] != 0 and progress_bars[area] != last_progress:
            #         progress_bars[area] -= 1/30
            #         if progress_bars[area] < 0:
            #             progress_bars[area] = 0
            self.send_message_to_listeners({
                'type': 'EYE_GAZE',
                'payload': {
                    'current_area': self.current_area,
                    'average_center_position': (-1, -1),
                    'relative_center_position': (-1, -1),
                    'selection_progress_bars_by_area': progress_bars,
                }
            })
            return
        if self.last_image_received is not None:
            img = self.last_image_received['payload']
            img = cv2.flip(img, 1)
            iris_landmarks = []
            eye_landmarks = []
            average_center_position = (-1, -1)
            relative_center_position = (-1, -1)
            results = self.iris.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            if results.face_landmarks_with_iris:
                for eye_contour_index in self.eye_contour_indices:
                    landmark = results.face_landmarks_with_iris.landmark[eye_contour_index]
                    eye_landmarks.append(
                        (int(landmark.x*img.shape[1]),
                         int(landmark.y*img.shape[0])))
                for index, landmark in enumerate(results.face_landmarks_with_iris.landmark):
                    if 467 < index:
                        iris_landmarks.append(
                            (int(landmark.x*img.shape[1]),
                             int(landmark.y*img.shape[0])))
            if len(iris_landmarks) > 0:
                relative_center_position = self.get_relative_center_position_and_ear(iris_landmarks, eye_landmarks)
                self.latest_center_positions.append(relative_center_position)
                if len(self.latest_center_positions) > self.positioning_samples:
                    self.latest_center_positions.pop(0)
                sum_x = sum([p[0] for p in self.latest_center_positions])
                sum_y = sum([p[1] for p in self.latest_center_positions])
                average_center_position = (
                        sum_x/len(self.latest_center_positions),
                        sum_y/len(self.latest_center_positions))
                if average_center_position[0] < self.thresholds['LEFT']:
                    self.current_area = (-1, self.current_area[1])
                elif self.thresholds['LEFT'] <= average_center_position[0] < self.thresholds['RIGHT']:
                    self.current_area = (0, self.current_area[1])
                elif self.thresholds['RIGHT'] <= average_center_position[0]:
                    self.current_area = (1, self.current_area[1])

                if average_center_position[1] < self.thresholds['TOP']:
                    self.current_area = (self.current_area[0], -1)
                elif average_center_position[1] >= self.thresholds['BOTTOM']:
                    self.current_area = (self.current_area[0], 1)
                else:
                    self.current_area = (self.current_area[0], 0)
                # print(average_center_position[1], self.thresholds['TOP'], self.thresholds['BOTTOM'])
            else:
                self.send_message_to_listeners({'type': 'EYE_NOT_FOUND'})
            self.last_image_received = None

            self.latest_areas.append(self.current_area)
            latest_areas_counts = Counter()
            for area in self.latest_areas:
                latest_areas_counts[area] += 1
            most_common = latest_areas_counts.most_common()
            clicked = any([x[1] > self.frames_threshold_needed_for_click for x in most_common])
            if clicked:
                self.latest_areas = []
                self.send_message_to_listeners({
                    'type': 'EYE_GAZE_CLICK',
                    'payload': {
                        'current_area': most_common[0][0]
                    }
                })
            progress_bars = {}
            # total_frames = sum([x[1] for x in most_common])
            total_frames = self.frames_threshold_needed_for_click
            last_most_common = progress_bars.copy()
            for area, frames in most_common:
                if clicked:
                    progress_bars[area] = 0
                else:
                    progress_bars[area] = frames/total_frames
            for area in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 0), (0, 1), (1, -1), (1, 0), (1, 1)]:
                if area in progress_bars.keys() and area != self.current_area:
                    progress_bars[area] -= 1/self.frames_threshold_needed_for_click*self.latest_areas.count(self.current_area)
            self.send_message_to_listeners({
                'type': 'EYE_GAZE',
                'payload': {
                    'current_area': self.current_area,
                    'average_center_position': average_center_position,
                    'relative_center_position': relative_center_position,
                    'selection_progress_bars_by_area': progress_bars,
                }
            })

    def process_received_message(self, message):
        if message['type'] == 'WEBCAM_CAPTURE':
            self.last_image_received = message
        elif message['type'] == 'CONFIG':
            if message['payload']['reload_config']:
                self.setup()
                reload_config_service.reloaded()
        if DEBUG:
            if message['type'] == 'PYGAME_MOUSE_POS':
                self.mouse_pos = message['payload']

    def consume(self):
        return self.get_gaze_area()
