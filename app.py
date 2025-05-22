
import os
import re
import uuid
import pdfplumber
from flask import Flask, request, render_template, send_file, url_for
from openpyxl import Workbook
from pdf2image import convert_from_path

UPLOAD_FOLDER = 'uploads'
IMAGEM_FOLDER = 'static/imagens'
EXCEL_FILE = 'resultados_processos.xlsx'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGEM_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def formatar_cnj_numerico(cnj_num):
    return f"{cnj_num[:7]}-{cnj_num[7:9]}.{cnj_num[9:13]}.{cnj_num[13]}.{cnj_num[14:16]}.{cnj_num[16:]}"

def encontrar_processos_cnj(texto):
    padrao_formatado = r'\b\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4}(?=\b|[^0-9])'
    padrao_numerico = r'\b\d{20}\b'
    padrao_espacado = r'\b(\d{7})\s*-\s*(\d{2})\.(\d{4})\.(\d{1,2})\.(\d{2})\.(\d{4})\b'

    encontrados_formatados = re.findall(padrao_formatado, texto)
    encontrados_puros = re.findall(padrao_numerico, texto)
    encontrados_espacados = re.findall(padrao_espacado, texto)

    formatados = [formatar_cnj_numerico(num) for num in encontrados_puros]
    espacados_formatados = [
        f"{a}-{b}.{c}.{d}.{e}.{f}" for a, b, c, d, e, f in encontrados_espacados
    ]

    return list(set(encontrados_formatados + formatados + espacados_formatados))

@app.route("/", methods=["GET", "POST"])
def index():
    resultados = []
    resumo_excel = []
    if request.method == "POST":
        arquivos = request.files.getlist("pdfs")
        for arquivo in arquivos:
            nome = arquivo.filename
            nome_id = f"{uuid.uuid4()}_{nome}"
            caminho = os.path.join(app.config["UPLOAD_FOLDER"], nome_id)
            pasta_imagens = os.path.join(IMAGEM_FOLDER, nome_id.replace(".pdf", ""))
            os.makedirs(pasta_imagens, exist_ok=True)
            arquivo.save(caminho)

            paginas_resultado = []
            try:
                # Gerar imagens
                imagens = convert_from_path(caminho, dpi=100)
                for i, img in enumerate(imagens):
                    img_path = os.path.join(pasta_imagens, f"pagina_{i+1}.png")
                    img.save(img_path, "PNG")

                # Extrair texto com CNJs
                with pdfplumber.open(caminho) as pdf:
                    for i, pagina in enumerate(pdf.pages):
                        texto = pagina.extract_text() or ""
                        processos = encontrar_processos_cnj(texto)
                        for proc in processos:
                            texto = texto.replace(proc, f"<mark>{proc}</mark>")
                        if processos and not any(r["arquivo"] == nome for r in resumo_excel):
                            resumo_excel.append({
                                "arquivo": nome,
                                "pagina": i + 1,
                                "cnj": processos[0]
                            })
                        paginas_resultado.append({
                            "pagina": i + 1,
                            "texto": texto.strip() if texto else "[Sem texto]",
                            "imagem": f"{nome_id.replace('.pdf', '')}/pagina_{i+1}.png"
                        })
            except Exception as e:
                paginas_resultado.append({
                    "pagina": "Erro",
                    "texto": f"Erro ao processar {nome}: {e}",
                    "imagem": None
                })

            resultados.append({
                "arquivo": nome,
                "paginas": paginas_resultado
            })

        wb = Workbook()
        ws = wb.active
        ws.title = "CNJs Encontrados"
        ws.append(["ARQUIVO PDF", "PÁGINA", "CNJ ENCONTRADO"])
        for item in resumo_excel:
            ws.append([item["arquivo"], item["pagina"], item["cnj"]])
        wb.save(EXCEL_FILE)

        return render_template("index.html", resultados=resultados)

    return render_template("index.html", resultados=[])

@app.route("/baixar_xlsx")
def baixar_xlsx():
    if os.path.exists(EXCEL_FILE):
        return send_file(EXCEL_FILE, as_attachment=True)
    return "Arquivo não encontrado", 404


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
