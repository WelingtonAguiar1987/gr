# BIBLIOTECAS IMPORTADAS:
import pandas as pd
import numpy as np
import datetime
from datetime import timedelta
import streamlit as st
import time
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors
except ImportError as e:
    st.error("Biblioteca reportlab não está instalada. Instale-a com: `pip install reportlab`")
    raise e
try:
    from streamlit_javascript import st_javascript
except ImportError as e:
    st.error("Biblioteca streamlit_javascript não está instalada. Instale-a com: `pip install streamlit-javascript`")
    raise e
from io import BytesIO
import os
import subprocess
import platform

# SIGLA E NOME DO ATIVO ANALISADO:
sigla_ativo = "MNQ=F"
nome_ativo = "NASDAQ 100 FUTUROS"

# CONFIGURAÇÃO DA PÁGINA:
st.set_page_config(page_title='GERENCIAMENTO DE RISCO', page_icon=':warning:', layout='wide')

# Inicializar session_state para armazenar resultados
if 'resultados' not in st.session_state:
    st.session_state.resultados = None

# Função para obter o horário local do navegador
def get_client_datetime():
    # Executa JavaScript para obter a data e hora local do navegador
    js_code = """
        new Date().toLocaleString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
    """
    try:
        client_datetime = st_javascript(js_code)
        # Verifica se o resultado é válido; caso contrário, usa o horário do servidor
        if client_datetime and isinstance(client_datetime, str) and len(client_datetime) >= 19:
            return client_datetime
        else:
            # Fallback para o horário do servidor se o JavaScript falhar
            return datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    except Exception:
        return datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')

# DICIONÁRIO DOS ATIVOS FUTUROS OPERADOS:
futuros = {
    'MICRO NASDAQ': {'sigla': 'MNQ=F', 'tick': 0.25, 'valor tick': 0.50},
    'MINI NASDAQ': {'sigla': 'NQ=F', 'tick': 0.25, 'valor tick': 5.00},
    'MICRO S&P500': {'sigla': 'MES=F', 'tick': 0.25, 'valor tick': 1.25},
    'MINI S&P500': {'sigla': 'ES=F', 'tick': 0.25, 'valor tick': 12.50},
    'MICRO DOW JONES': {'sigla': 'MYM=F', 'tick': 1.00, 'valor tick': 0.50},
    'MINI DOW JONES': {'sigla': 'YM=F', 'tick': 1.00, 'valor tick': 5.00},   
    'MICRO RUSSELL2000': {'sigla': 'M2K=F', 'tick': 0.10, 'valor tick': 0.50},
    'MINI RUSSELL2000': {'sigla': 'RTY=F', 'tick': 0.10, 'valor tick': 5.00},  
    'MICRO OURO': {'sigla': 'MGC=F', 'tick': 0.10, 'valor tick': 1.00},
    'MINI OURO': {'sigla': 'GC=F', 'tick': 0.10, 'valor tick': 10.00},
    'MICRO PETRÓLEO WTI': {'sigla': 'MCL=F', 'tick': 0.01, 'valor tick': 100.00}
}

# Criação e configuração das variáveis
st.markdown("<h1 style='text-align: center; color: white;'>GERENCIAMENTO DE RISCO ⚠️</h1>", unsafe_allow_html=True)
ativo = st.selectbox("Ativo Operado:", list(futuros.keys()))
tipo_operacao = st.selectbox("Posição Aberta:", ["COMPRA", "VENDA"])
preco_abertura_posicao = float(st.number_input("Preço Abertura de Posição:", format="%.2f"))
preco_stop = float(st.number_input("Preço do Stop:", format="%.2f"))
preco_alvo = float(st.number_input("Preço do Alvo:", format="%.2f"))

# CONDICIONAL PARA SELECIONAR CONTRATOS, BARRIS OU ONÇAS TROY:
if ativo == 'MICRO NASDAQ':
    total_contratos = int(st.number_input("Quantidade Contratos:", min_value=0, max_value=85))
elif ativo == 'MINI NASDAQ':
    total_contratos = int(st.number_input("Quantidade Contratos:", min_value=0, max_value=17))
elif ativo == 'MICRO S&P500':
    total_contratos = int(st.number_input("Quantidade Contratos:", min_value=0, max_value=85)) 
elif ativo == 'MINI S&P500':
    total_contratos = int(st.number_input("Quantidade Contratos:", min_value=0, max_value=17))
elif ativo == 'MICRO DOW JONES':
    total_contratos = int(st.number_input("Quantidade Contratos:", min_value=0, max_value=17)) 
elif ativo == 'MINI DOW JONES':
    total_contratos = int(st.number_input("Quantidade Contratos:", min_value=0, max_value=17))   
elif ativo == 'MICRO RUSSELL2000':
    total_contratos = int(st.number_input("Quantidade Contratos:", min_value=0, max_value=17))
elif ativo == 'MINI RUSSELL2000':
    total_contratos = int(st.number_input("Quantidade Contratos:", min_value=0, max_value=17))   
elif ativo == 'MICRO OURO':
    total_contratos = float(st.number_input("Quantidade Fracionada da Onças Troy:", min_value=0.01, max_value=1.000))
elif ativo == 'MINI OURO':
    total_contratos = float(st.number_input("Quantidade Fracionada da Onças Troy:", min_value=0.01, max_value=1.000))
elif ativo == 'MICRO PETRÓLEO WTI':
    total_contratos = float(st.number_input("Quantidade Fracionada do Barril:", min_value=0.01, max_value=1.000))    
         
if total_contratos == 0:
    st.error('SELECIONE UMA QUANTIDADE DE CONTRATOS PARA GERAR O CÁLCULO!')

capital_total = float(st.number_input("Capital Total da Conta:", format="%.2f"))

# Função para calcular e exibir os resultados
def calculate():
    ativo_detalhes = futuros[ativo]
    ponto_tick = 4  # Ajuste conforme necessário

    # Calcula os alvos e stops
    if tipo_operacao == 'COMPRA':
        alvo = preco_alvo - preco_abertura_posicao
        stop = preco_abertura_posicao - preco_stop
    elif tipo_operacao == 'VENDA':
        alvo = preco_abertura_posicao - preco_alvo
        stop = preco_stop - preco_abertura_posicao

    # Calcula o lucro e a perda
    lucro = ((ativo_detalhes['valor tick'] * ponto_tick) * abs(alvo)) * total_contratos
    perda = ((ativo_detalhes['valor tick'] * ponto_tick) * abs(stop)) * total_contratos

    # Calcula a variação de lucro e perda com base no capital total
    var_lucro = (lucro / capital_total) * 100
    var_perda = (perda / capital_total) * 100

    # Calcula o Payoff
    try:
        payoff = lucro / perda
    except ZeroDivisionError:
        payoff = "indefinido"

    # Exibe os resultados
    st.write(f'Nesta {tipo_operacao.upper()} o seu ALVO é de {abs(alvo):.2f} pontos, com LUCRO de US$ {lucro:.2f}.')
    st.write(f'Nesta {tipo_operacao.upper()} o seu STOP é de {abs(stop):.2f} pontos, com PERDA de US$ {perda:.2f}.')
    st.write(f'O PAYOFF desta operação é {payoff:.2f}.')
    st.write(f'A variação de LUCRO em relação ao capital total é de {var_lucro:.2f}%.')
    st.write(f'A variação de PERDA em relação ao capital total é de {var_perda:.2f}%.')
    
    # Armazena os resultados no session_state
    st.session_state.resultados = {
        'ativo': ativo,
        'tipo_operacao': tipo_operacao,
        'preco_abertura': preco_abertura_posicao,
        'preco_alvo': preco_alvo,
        'preco_stop': preco_stop,
        'total_contratos': total_contratos,
        'capital_total': capital_total,
        'alvo_pontos': abs(alvo),
        'stop_pontos': abs(stop),
        'lucro': lucro,
        'perda': perda,
        'payoff': payoff,
        'var_lucro': var_lucro,
        'var_perda': var_perda
    }

# Função para gerar o PDF
def generate_pdf(resultados):
    try:
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Título
        c.setFont("Helvetica-Bold", 16)
        c.setFillColor(colors.darkblue)
        c.drawCentredString(width / 2, height - 50, "Relatório de Gerenciamento de Risco")
        c.setFont("Helvetica", 12)
        c.setFillColor(colors.black)
        # Usar o horário local do navegador
        c.drawCentredString(width / 2, height - 70, f"Data: {get_client_datetime()}")

        # Dados para a tabela
        data = [
            ["Campo", "Valor"],
            ["Ativo Operado", resultados['ativo']],
            ["Tipo de Operação", resultados['tipo_operacao']],
            ["Preço de Abertura", f"US$ {resultados['preco_abertura']:.2f}"],
            ["Preço do Alvo", f"US$ {resultados['preco_alvo']:.2f}"],
            ["Preço do Stop", f"US$ {resultados['preco_stop']:.2f}"],
            ["Quantidade de Contratos", f"{resultados['total_contratos']}"],
            ["Capital Total", f"US$ {resultados['capital_total']:.2f}"],
            ["Alvo", f"{resultados['alvo_pontos']:.2f} pontos"],
            ["Stop", f"{resultados['stop_pontos']:.2f} pontos"],
            ["Lucro", f"US$ {resultados['lucro']:.2f}"],
            ["Perda", f"US$ {resultados['perda']:.2f}"],
            ["Payoff", f"{resultados['payoff']:.2f}"],
            ["Variação de Lucro", f"{resultados['var_lucro']:.2f}%"],
            ["Variação de Perda", f"{resultados['var_perda']:.2f}%"]
        ]

        # Criar tabela
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            # Cores para destacar lucro e perda
            ('TEXTCOLOR', (1, 10), (1, 10), colors.green),  # Lucro
            ('TEXTCOLOR', (1, 11), (1, 11), colors.red),    # Perda
            ('TEXTCOLOR', (1, 13), (1, 13), colors.green),  # Variação de Lucro
            ('TEXTCOLOR', (1, 14), (1, 14), colors.red),    # Variação de Perda
        ]))

        # Ajustar largura das colunas
        table_width = width - 100
        col_widths = [table_width * 0.5, table_width * 0.5]
        table._argW = col_widths

        # Posicionar a tabela com espaço adicional
        table.wrapOn(c, table_width, height)
        table.drawOn(c, 50, height - 370)  # Mantido o espaço de uma linha

        c.showPage()
        c.save()
        buffer.seek(0)
        
        # Salvar o PDF localmente
        output_dir = "relatorios_gerenciamento_risco"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"{output_dir}/relatorio_gerenciamento_risco_{timestamp}.pdf"
        with open(pdf_filename, "wb") as f:
            f.write(buffer.read())
        
        buffer.seek(0)
        return buffer, pdf_filename, output_dir
    except Exception as e:
        st.error(f"Erro ao gerar o PDF: {str(e)}")
        return None, None, None

# Função para abrir a pasta onde o PDF foi salvo
def open_folder(folder_path):
    try:
        if platform.system() == "Windows":
            os.startfile(folder_path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", folder_path])
        else:  # Linux
            subprocess.run(["xdg-open", folder_path])
        st.success(f"Pasta {folder_path} aberta com sucesso!")
    except Exception as e:
        st.error(f"Erro ao abrir a pasta: {str(e)}")

# Botão para calcular
if st.button('Calcular'):
    if total_contratos == 0:
        st.error("Por favor, selecione uma quantidade de contratos válida antes de calcular.")
    else:
        try:
            calculate()
            st.success("Cálculo realizado com sucesso!")
        except Exception as e:
            st.error(f"Erro ao realizar o cálculo: {str(e)}")

# Botão para gerar PDF e abrir pasta
if st.session_state.resultados is not None:
    if st.button('Gerar PDF'):
        resultados = st.session_state.resultados
        pdf_buffer, pdf_filename, output_dir = generate_pdf(resultados)
        if pdf_buffer and pdf_filename and output_dir:
            st.download_button(
                label="Baixar Relatório em PDF",
                data=pdf_buffer,
                file_name=os.path.basename(pdf_filename),
                mime="application/pdf"
            )
            st.success(f"PDF gerado e salvo em: {pdf_filename}")
            
            # Botão para abrir a pasta
            if st.button('Abrir Pasta do Arquivo'):
                open_folder(output_dir)
else:
    st.warning("Realize o cálculo antes de gerar o PDF.")