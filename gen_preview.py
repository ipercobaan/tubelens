"""Generate preview.html: UI yang sama, data asli di-embed (tanpa backend)."""
import json
import re

with open("static/index.html", encoding="utf-8") as f:
    html = f.read()
with open("preview_data.json", encoding="utf-8") as f:
    data = json.load(f)

data_js = "<script>\nconst DATA = " + json.dumps(data, ensure_ascii=False) + ";\n</script>"

new_js = """
async function loadNiches(){
  const sel = document.getElementById('f-niche');
  DATA.niches.forEach(n => { const o=document.createElement('option'); o.value=n.slug; o.textContent=`${n.name} (${n.videos} video)`; sel.appendChild(o); });
}""".strip()

new_load = """
async function load(){
  const grid=document.getElementById('grid'), status=document.getElementById('status');
  grid.innerHTML=''; status.textContent='Memuat...';
  const niche=document.getElementById('f-niche').value, q=document.getElementById('f-q').value.trim().toLowerCase();
  const sort=document.getElementById('f-sort').value;
  let data = DATA.videos.filter(v => (!niche || v.niche===niche) && (!q || (v.title||'').toLowerCase().includes(q)));
  if(tab==='outlier') data = data.filter(v => (v.outlier_score||0) >= 2);
  const key = tab==='outlier' ? 'outlier_score' : (sort==='latest' ? 'published_at' : (sort==='outlier' ? 'outlier_score' : 'views'));
  data = data.slice().sort((a,b)=>((b[key]||0) > (a[key]||0) ? 1 : -1)).slice(0,60);
  status.textContent = data.length ? `${data.length} video (data preview, ${DATA.videos.length} total di database)` : 'Tidak ada hasil.';
  data.forEach(v=>{ renderCard(grid, v); });
}""".strip()

# ganti fungsi loadNiches
html = re.sub(r"async function loadNiches\(\)\{.*?\n\}", new_js + "\n", html, flags=re.DOTALL)
# ganti fungsi load (dari 'async function load(){' sampai sebelum 'function escapeHtml')
html = re.sub(r"async function load\(\)\{.*?function escapeHtml",
              new_load + "\nfunction escapeHtml", html, flags=re.DOTALL)
# renderCard: ekstrak isi forEach lama jadi fungsi
old_foreach = """  data.forEach(v=>{
    const el=document.createElement('div'); el.className='card';"""
new_rendercard = """function renderCard(grid, v){
    const el=document.createElement('div'); el.className='card';"""
html = html.replace(old_foreach.strip(), new_rendercard)
html = html.replace("""    grid.appendChild(el);
  });
}""", """    grid.appendChild(el);
}""")

# label preview
html = html.replace("(codename, MVP)", "(codename, PREVIEW — data asli hasil crawl)")
# inject data sebelum script utama
html = html.replace("<script>", data_js + "\n<script>", 1)

with open("preview.html", "w", encoding="utf-8") as f:
    f.write(html)
print("preview.html OK,", len(html), "bytes")
