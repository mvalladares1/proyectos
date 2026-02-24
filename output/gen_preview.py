import html2image

hti = html2image.Html2Image(
    output_path='output',
    size=(378, 378),
    browser_executable=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
)

html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
body { font-family: Arial, sans-serif; padding: 0; margin: 0; width: 100mm; height: 100mm; background: white; }
.recuadro { padding: 5mm 5mm; margin: 2mm; box-sizing: border-box; font-size: 12px; line-height: 1.6; }
.campo { margin: 1px 0; }
.campo .label { font-weight: normal; }
.campo .valor { font-weight: bold; }
</style></head><body>
<div class="recuadro">
<div class="campo"><span class="label">MATERIAL CODE: </span><span class="valor">RIRASPBERRY</span></div>
<div class="campo"><span class="label">PRODUCT NAME: </span><span class="valor">Frozen Raspberry 12-24 mm</span></div>
<div class="campo"><span class="label">NET WEIGHT: </span><span class="valor">10KG</span></div>
<div class="campo"><span class="label">PRODUCTION DATE: </span><span class="valor">19-02-2026</span></div>
<div class="campo"><span class="label">BEST BEFORE: </span><span class="valor">19-02-2028</span></div>
<div class="campo"><span class="label">BATCH NO.: </span><span class="valor">0012345 / PACK0012345</span></div>
<div class="campo"><span class="label">STORAGE TEMPERATURE: </span><span class="valor">-18&deg;C</span></div>
<div class="campo"><span class="label">ORIGIN: </span><span class="valor">CHILE</span></div>
<div class="campo"><span class="label">CARTON NO: </span><span class="valor">1</span></div>
<div class="campo"><span class="label">PRODUCT FOR </span><span class="valor">LACO</span></div>
</div></body></html>"""

hti.screenshot(html_str=html, save_as='etiqueta_iqfa_preview.png')
print('OK - saved to output/etiqueta_iqfa_preview.png')
