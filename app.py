
import os
import re
import uuid
import PyPDF2
from flask import Flask, request, render_template, send_file
from openpyxl import Workbook

UPLOAD_FOLDER = 'uploads'
EXCEL_FILE = 'resultados_processos.xlsx'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def formatar_cnj_numerico(cnj_num):
    return f"{cnj_num[:7]}-{cnj_num[7:9]}.{cnj_num[9:13]}.{cnj_num[13]}.{cnj_num[14:16]}.{cnj_num[16:]}"

def encontrar_processos_cnj(texto):
    padrao_formatado = r'\b\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4}\b'
    padrao_numerico = r'\b\d{20}\b'
    encontrados_formatados = re.findall(padrao_formatado, texto)
    encontrados_puros = re.findall(padrao_numerico, texto)
    formatados = [formatar_cnj_numerico(num) for num in encontrados_puros]
    return list(set(encontrados_formatados + formatados))

@app.route("/", methods=["GET", "POST"])
def index():
    resultados = []
    resumo_excel = []
    if request.method == "POST":
        arquivos = request.files.getlist("pdfs")
        for arquivo in arquivos:
            nome = arquivo.filename
            caminho = os.path.join(app.config["UPLOAD_FOLDER"], f"{uuid.uuid4()}_{nome}")
            arquivo.save(caminho)

            paginas_resultado = []
            try:
                with open(caminho, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for i, pagina in enumerate(reader.pages):
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
                        })
            except Exception as e:
                paginas_resultado.append({
                    "pagina": "Erro",
                    "texto": f"Erro ao processar {nome}: {e}"
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
    import threading
    import webbrowser

    def abrir_navegador():
        webbrowser.open_new("http://127.0.0.1:5000")

    threading.Timer(1.25, abrir_navegador).start()
    app.run(debug=True)
