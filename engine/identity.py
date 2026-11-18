
import numpy as np


class IdentityManager:

    def __init__(self, threshold=0.363):

        self.threshold = threshold
        self.known_people = []

    def load_people(self, folder):

        self.known_people = []

        for file in folder.glob("*.npz"):

            try:
                with np.load(file, allow_pickle=False) as data:

                    name = str(data["name"].item())
                    embeddings = data["embeddings"]

                    for embedding in embeddings:

                        embedding = np.asarray(
                            embedding,
                            dtype=np.float32
                        ).flatten()

                        norm = np.linalg.norm(embedding)

                        if norm == 0:
                            continue

                        embedding = embedding / norm

                        self.known_people.append({
                            "name": name,
                            "embedding": embedding
                        })

                print(f"Loaded authorized person: {name}")

            except Exception as error:

                print(f"Could not load {file.name}: {error}")

        print(
            f"\nTotal authorized face samples: {len(self.known_people)}"
        )

    def identify(self, embedding):

        if not self.known_people:
            return "UNKNOWN", 0.0

        embedding = np.asarray(
            embedding,
            dtype=np.float32
        ).flatten()

        norm = np.linalg.norm(embedding)

        if norm == 0:
            return "UNKNOWN", 0.0

        embedding = embedding / norm

        best_name = "UNKNOWN"
        best_score = -1.0

        for person in self.known_people:

            known_embedding = person["embedding"]

            score = float(
                np.dot(embedding, known_embedding)
            )

            if score > best_score:

                best_score = score
                best_name = person["name"]

        if best_score >= self.threshold:
            return best_name, best_score

        return "UNKNOWN", best_score
