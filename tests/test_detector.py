import unittest
import csv

from detector import detect


class MyTestCase(unittest.TestCase):
    def test_detector(self):
        with open('tests/test_detector.csv', "r") as f_obj:
            reader = csv.reader(f_obj, delimiter=';')
            for row in reader:
                with self.subTest(row=row[0]):
                    res = detect(row[0])
                    if res['detected']:
                        self.assertEqual(row[1], res['material'])
                        self.assertEqual(row[2], res['dimension'])
                        self.assertEqual(row[3], 'Да')
                        # self.assertEqual(row[1] + row[2] + row[3], res['material'] + res['dimension'] + 'Да', row[0])
                    else:
                        self.assertEqual(row[3], 'Нет')


if __name__ == '__main__':
    unittest.main()
