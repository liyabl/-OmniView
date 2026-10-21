from PIL import Image, ImageDraw, ImageFont
import os
base=r"F:\DeepSeek默认\OmniView3\test-evidence"
files=[f for f in sorted(os.listdir(base)) if f.endswith('.png') and f!='00_contact_sheet.png']
cols=3; cell=(420,330); labelh=34; rows=(len(files)+cols-1)//cols
sheet=Image.new('RGB',(cols*cell[0],rows*(cell[1]+labelh)),(15,23,42)); draw=ImageDraw.Draw(sheet)
try: font=ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf",16)
except Exception: font=ImageFont.load_default()
for i,f in enumerate(files):
    im=Image.open(os.path.join(base,f)).convert('RGB'); im.thumbnail((cell[0]-20,cell[1]-20))
    x=(i%cols)*cell[0]; y=(i//cols)*(cell[1]+labelh)
    sheet.paste(im,(x+(cell[0]-im.width)//2,y+(cell[1]-im.height)//2))
    draw.text((x+10,y+cell[1]+6),f,fill=(220,230,245),font=font)
sheet.save(os.path.join(base,'00_contact_sheet.png')); print(len(files),sheet.size)
