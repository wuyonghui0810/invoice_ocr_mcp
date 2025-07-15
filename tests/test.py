from rapidocr import RapidOCR

engine = RapidOCR()

img_url = "fp.png"
result = engine(img_url, return_word_box=True, return_single_char_box=True)
print(result)

result.vis("vis_result.jpg")
print(result.to_json())