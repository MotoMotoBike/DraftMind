import cv2

image = cv2.imread("screenshot.png")

# Поменяй эти значения при необходимости
x = 180
y = 0
w = 1560
h = 120

draft = image[y:y+h, x:x+w]

cv2.imshow("Draft", draft)
cv2.waitKey(0)
cv2.destroyAllWindows()
