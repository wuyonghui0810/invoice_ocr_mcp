# from rapidocr import RapidOCR

# engine = RapidOCR()

# img_url = "fp.png"
# result = engine(img_url, return_word_box=True, return_single_char_box=True)
# print(result)

# result.vis("vis_result.jpg")
# print(result.to_json())

import os

if __name__ == "__main__":
    api_token = os.getenv('MODELSCOPE_API_TOKEN')
    print(f"MODELSCOPE_API_TOKEN: {api_token}")