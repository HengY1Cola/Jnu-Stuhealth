from __future__ import print_function
from time import time
import cv2 as cv
import numpy as np
import requests
from gaps.genetic_algorithm import GeneticAlgorithm


class Gaps:
    def __init__(self, imgUrl):
        self.url = imgUrl
        self.generations = 20
        self.population = 600
        self.piece_size = 80

    def getRes(self):
        resp = requests.get(self.url)
        image = np.asarray(bytearray(resp.content), dtype="uint8")
        image = cv.imdecode(image, cv.IMREAD_COLOR)
        image = cv.cvtColor(image, cv.COLOR_BGR2RGB)
        print(f"[*] Start Do Gaps {self.url}")
        start = time()
        algorithm = GeneticAlgorithm(image, self.piece_size, 200, 20)
        solution = algorithm.start_evolution(False)
        end = time()
        print("[*] Done in {0:.3f} s".format(end - start))
        solution.to_image()
        print('[*] PieceMapping = ', solution.getPieceMapping())
        return solution.getPieceMapping()

    def getLocation(self):
        resMap, total, first = self.getRes(), 0, []
        for k, v in resMap.items():
            if k == v:
                total += 1
                continue
            if not first:
                first = [k, v]
                continue
        if total == 6 and first:
            return first
        else:
            return []

    def run(self):
        res = self.getLocation()
        if not res:
            return res
        if res[0] > res[1]:
            return [res[1], res[0]]
        return res


if __name__ == "__main__":
    # 用于测试
    url = "https://necaptcha.nosdn.127.net/5c0fac1ddd044630b5daaae2aac85bbc.jpg"
    final = Gaps(url).run()
    print(final)
