
class FaceTracker:

    def __init__(self, iou_threshold=0.30, max_missing_seconds=1.5):
        self.iou_threshold = iou_threshold
        self.max_missing_seconds = max_missing_seconds
        self.tracks = {}
        self.next_id = 1

    @staticmethod
    def calculate_iou(box1, box2):
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2

        left = max(x1, x2)
        top = max(y1, y2)
        right = min(x1 + w1, x2 + w2)
        bottom = min(y1 + h1, y2 + h2)

        intersection = max(0, right - left) * max(0, bottom - top)
        union = (w1 * h1) + (w2 * h2) - intersection

        return intersection / union if union > 0 else 0.0

    def update(self, detections, current_time):
        assigned = set()
        active = []

        for box, name, score in detections:
            best_id = None
            best_iou = 0.0

            for track_id, track in self.tracks.items():
                if track_id in assigned:
                    continue

                iou = self.calculate_iou(box, track["box"])

                if iou > best_iou:
                    best_iou = iou
                    best_id = track_id

            if best_id is not None and best_iou >= self.iou_threshold:
                track_id = best_id
                track = self.tracks[track_id]
                track["box"] = box
                track["last_seen"] = current_time

            else:
                track_id = self.next_id
                self.next_id += 1

                track = {
                    "id": track_id,
                    "box": box,
                    "first_seen": current_time,
                    "last_seen": current_time,
                    "unknown_since": None,
                    "evidence_saved": False,
                    "evidence_path": None,
                    "event_recorded": False,
                    "alerted": False,
                    "authorized_logged": False
                }

                self.tracks[track_id] = track

            assigned.add(track_id)

            previous_name = track.get("name")
            track["name"] = name
            track["score"] = score

            if name == "UNKNOWN":
                if track["unknown_since"] is None:
                    track["unknown_since"] = current_time

                track["authorized_logged"] = False

            else:
                track["unknown_since"] = None
                track["evidence_saved"] = False
                track["evidence_path"] = None
                track["event_recorded"] = False
                track["alerted"] = False

            active.append(track)

        expired = [
            track_id
            for track_id, track in self.tracks.items()
            if current_time - track["last_seen"] > self.max_missing_seconds
        ]

        for track_id in expired:
            del self.tracks[track_id]

        return active
