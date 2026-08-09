# -*- coding: utf-8 -*-
import json
from pathlib import Path
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Audit 5S - Cellula 4.0",
    page_icon="✅",
    layout="wide",
)

AREE = {
    "1S - Scegliere": [
        ("Materiali", "Sono presenti articoli di scorta nel posto di lavoro (tipologia)?", [0,1,2,3,4]),
        ("Strumenti e materiali 1/2", "Tutti gli strumenti e materiali scelti sono quelli realmente utilizzati?", [0,4]),
        ("Strumenti e materiali 2/2", "I quantitativi individuati sono quelli di reale necessità?", [0,4]),
        ("Controllo visivo", "Ci sono materiali e/o strumenti che possono intralciare il lavoro?", [0,1,2,3,4]),
        ("Documentazione", "La documentazione necessaria è presente sulla postazione di lavoro?", [0,4]),
    ],
    "2S - Sistemare": [
        ("Materiali", "Il materiale necessario è a portata di mano?", [0,1,2,3,4]),
        ("Spazi", "Sono disposti in modo da ottimizzare l'economicità dei movimenti?", [0,4]),
        ("Indicatori di qualità", "Sono presenti segnali kanban su tutti i materiali da rifornire?", [0,1,2,3,4]),
        ("Identificazione", "Tutte le etichette indicative sono presenti e ben leggibili?", [0,1,2,3,4]),
        ("Strumenti e materiali", "Sono sistemati secondo le scelte fatte?", [0,1,2,3,4]),
    ],
    "3S - Sorvegliare": [
        ("Postazione di lavoro", "È in ordine e pulita?", [0,4]),
        ("Accumulo materiali di scarto", "Nella postazione di lavoro è presente materiale di scarto (scatole vuote, imballi, ecc.)?", [0,4]),
        ("Apparecchiature e strumenti", "Sono presenti strumenti/apparecchiature non funzionanti sulla postazione di lavoro?", [0,1,2,3,4]),
        ("Armadi, scaffalature, contenitori e spazi", "Sono ben identificati e segnalati (comprese apparecchiature su ruote)?", [0,1,2,3,4]),
        ("Rifornimento kanban", "Riscontrate quantità inferiori alla minima?", [0,4]),
    ],
    "4S - Standardizzare": [
        ("Responsabilità 1/2", 'I "5 minuti" sono standardizzati e vengono effettuati regolarmente?', [0,4]),
        ("Responsabilità 2/2", 'Gli orari dei "5 minuti" vengono rispettati?', [0,1,2,3,4]),
        ("Documentazione", "Esistono correzioni sulla documentazione della postazione di lavoro?", [0,4]),
        ("Identificazione responsabili", "L'elenco del personale addetto al controllo/riapprovvigionamento è presente, compilato ed aggiornato?", [0,4]),
        ("Aggiornamento documentazione", "La documentazione ove siano state individuate delle modifiche è stata corretta secondo le indicazioni dell'audit precedente?", [0,4]),
    ],
    "5S - Sostenere": [
        ("Sicurezza di emergenza", "Estintori, uscite di sicurezza e pannelli di controllo non sono ostruiti?", [0,1,2,3,4]),
        ("5S Audits", "Questo audit è fatto nella data stabilita?", [0,4]),
        ("Controllo del sistema 1/2", "Le azioni di miglioramento evidenziate nell'ultimo audit sono state programmate?", [0,4]),
        ("Controllo del sistema 2/2", "Le azioni di miglioramento evidenziate nell'ultimo audit sono state sviluppate?", [0,4]),
        ("Regole e procedure", "Riguardo le 5S, le norme e le procedure sono conosciute da tutti gli operatori?", [0,4]),
    ],
}

SCALA = {
    0: "Quattro o più varianze",
    1: "Tre varianze",
    2: "Due varianze",
    3: "Una varianza",
    4: "Nessuna varianza",
}

DB = Path(__file__).with_name("audit_5s_records.json")

def load_records():
    if not DB.exists():
        return []
    try:
        return json.loads(DB.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_records(records):
    DB.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

def add_months(d, months):
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    days = [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28,
            31,30,31,30,31,31,30,31,30,31]
    return date(y, m, min(d.day, days[m-1]))

def status_label(total):
    if total >= 90:
        return "Consolidato"
    if total >= 80:
        return "Buono"
    if total >= 70:
        return "Da consolidare"
    if total >= 60:
        return "Criticità significative"
    return "Critico"

def next_audit(d, total, area_scores, answers):
    if total >= 90:
        nxt, reason = add_months(d, 6), "mantenimento molto buono"
    elif total >= 80:
        nxt, reason = add_months(d, 3), "buon mantenimento, con aree da consolidare"
    elif total >= 70:
        nxt, reason = add_months(d, 2), "mantenimento parziale"
    elif total >= 60:
        nxt, reason = add_months(d, 1), "criticità significative"
    else:
        nxt, reason = d + timedelta(days=14), "mantenimento insufficiente"

    notes = [reason]

    if any(v == 0 for v in answers.values()):
        nxt = min(nxt, d + timedelta(days=30))
        notes.append("presente almeno un item con punteggio 0")

    if answers.get(21) == 0:
        nxt = min(nxt, d + timedelta(days=14))
        notes.append("criticità sulla sicurezza di emergenza")

    if any(v < 12 for v in area_scores.values()):
        nxt = min(nxt, d + timedelta(days=30))
        notes.append("almeno una delle 5S è inferiore a 12/20")

    return nxt, "; ".join(dict.fromkeys(notes))

def previous_record(records, zona, setting):
    candidates = [
        (i, r) for i, r in enumerate(records)
        if r.get("zona_ospedale","").strip().lower() == zona.strip().lower()
        and r.get("setting","").strip().lower() == setting.strip().lower()
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[1].get("data_effettuazione",""), x[0]), reverse=True)
    return candidates[0][1]

def score_buttons(item_no, allowed):
    current = st.session_state.get(f"score_{item_no}")
    cols = st.columns(5)
    for score, col in enumerate(cols):
        with col:
            if st.button(
                str(score),
                key=f"btn_{item_no}_{score}",
                disabled=score not in allowed,
                type="primary" if current == score else "secondary",
                use_container_width=True,
            ):
                st.session_state[f"score_{item_no}"] = score
                st.rerun()
    if allowed == [0,4]:
        st.caption("Item dicotomico: SÌ = 4, NO = 0. I punteggi 1-2-3 non sono applicabili.")
    if current is not None:
        st.caption(f"Selezionato: **{current} - {SCALA[current]}**")
    return current

def reset_current_audit():
    for key in list(st.session_state.keys()):
        if key.startswith("score_") or key.startswith("obs_"):
            del st.session_state[key]

def history_dataframe(records):
    rows = []
    for i, r in enumerate(records, start=1):
        rows.append({
            "Audit": i,
            "Data": r.get("data_effettuazione",""),
            "Ospedale": r.get("zona_ospedale",""),
            "Setting": r.get("setting",""),
            "Auditor": r.get("auditor",""),
            "Totale /100": r.get("totale",""),
            "Score /20": r.get("score_20",""),
            "Stato": status_label(int(r.get("totale", 0))) if str(r.get("totale","")).strip() != "" else "",
            "Prossimo audit proposto": r.get("prossimo_audit_proposto",""),
            "Motivazione": r.get("motivazione_rivalutazione",""),
        })
    return pd.DataFrame(rows)

st.title("Audit 5S - Cellula 4.0")
st.caption("Scheda digitale per il monitoraggio del mantenimento dei cantieri 5S")

records = load_records()

with st.sidebar:
    st.header("Dati dell'audit")
    zona = st.text_input("Zona / Ospedale")
    setting = st.text_input("Setting e ambito")
    auditor = st.text_input("Auditor")
    data_stimata = st.date_input("Data programmata", value=date.today())
    data_effettuazione = st.date_input("Data effettuazione", value=date.today())

    prev = previous_record(records, zona, setting)
    if prev:
        st.info(f"Ultimo audit registrato: {prev.get('data_effettuazione','')} - {prev.get('totale','')}/100")
    else:
        st.caption("Punteggio precedente: non disponibile nello storico.")

    st.divider()
    st.markdown("### Scala di valutazione")
    for k,v in SCALA.items():
        st.write(f"**{k}** - {v}")
    st.caption("Negli item SÌ=4 / NO=0, i valori 1-2-3 sono disabilitati.")

    st.divider()
    if st.button("Nuovo audit / azzera compilazione", use_container_width=True):
        reset_current_audit()
        st.rerun()

all_items = []
n = 1
for area, items in AREE.items():
    for title, criterion, allowed in items:
        all_items.append((n, area, title, criterion, allowed))
        n += 1

completed = sum(st.session_state.get(f"score_{i}") is not None for i,*_ in all_items)
st.progress(completed/25, text=f"Avanzamento: {completed}/25 item valutati")

tabs = st.tabs(list(AREE.keys()))
n = 1
for tab, (area, items) in zip(tabs, AREE.items()):
    with tab:
        st.subheader(area)
        for title, criterion, allowed in items:
            st.markdown(f"#### {n}. {title}")
            st.write(criterion)
            score_buttons(n, allowed)
            st.text_area(
                "Osservazioni / azioni",
                key=f"obs_{n}",
                height=72,
                placeholder="Annotare eventuali varianze, criticità o azioni di miglioramento..."
            )
            st.divider()
            n += 1

answers = {
    i: st.session_state.get(f"score_{i}")
    for i,*_ in all_items
    if st.session_state.get(f"score_{i}") is not None
}
obs = {i: st.session_state.get(f"obs_{i}", "") for i,*_ in all_items}

st.header("Risultati dell'audit 5S")

if completed < 25:
    st.warning(
        f"Audit non ancora completato: {completed}/25 item valutati. "
        "Il punteggio finale e la data di rivalutazione saranno calcolati solo a compilazione completa."
    )
else:
    area_scores = {}
    start = 1
    for area in AREE:
        area_scores[area] = sum(answers[i] for i in range(start, start+5))
        start += 5

    total = sum(area_scores.values())
    score20 = total / 5
    nextdate, reason = next_audit(data_effettuazione, total, area_scores, answers)

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Punteggio complessivo", f"{total}/100")
    c2.metric("Punteggio medio 5S", f"{score20:.1f}/20")
    c3.metric("Stato", status_label(total))
    c4.metric("Item con punteggio 0", sum(v == 0 for v in answers.values()))
    c5.metric("Data prossimo audit proposta", nextdate.strftime("%d/%m/%Y"))

    st.info(f"Motivazione della rivalutazione proposta: {reason}.")
    st.caption(
        "La periodicità è una proposta progettuale costruita per il prototipo; "
        "non deriva da una regola esplicitata nell'immagine del manuale."
    )

    left, right = st.columns([1,1.3])
    with left:
        df = pd.DataFrame({
            "Area": list(area_scores.keys()),
            "Punteggio": list(area_scores.values()),
            "Massimo": [20]*5
        })
        st.dataframe(df, hide_index=True, use_container_width=True)

        if prev:
            delta = total - int(prev.get("totale",0))
            st.metric("Variazione rispetto all'audit precedente", f"{delta:+d} punti")

    with right:
        labels = ["1S","2S","3S","4S","5S"]
        vals = list(area_scores.values())
        fig = go.Figure(go.Scatterpolar(
            r=vals+[vals[0]],
            theta=labels+[labels[0]],
            fill="toself",
            name="Audit attuale"
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0,20], dtick=2)),
            showlegend=False,
            height=420,
        )
        st.plotly_chart(fig, use_container_width=True)

    critical = []
    for i, area, title, criterion, allowed in all_items:
        if answers[i] <= 2:
            critical.append({
                "Item": i,
                "Area": area,
                "Voce": title,
                "Punteggio": answers[i],
                "Osservazioni": obs[i],
            })
    if critical:
        st.subheader("Priorità di miglioramento")
        st.dataframe(pd.DataFrame(critical), hide_index=True, use_container_width=True)

    campi_obbligatori_ok = bool(zona.strip() and setting.strip() and auditor.strip())

    if not campi_obbligatori_ok:
        st.warning(
            "Prima di salvare compila i campi obbligatori: "
            "Zona / Ospedale, Setting e ambito, Auditor."
        )

    if st.button(
        "Salva audit",
        type="primary",
        use_container_width=True,
        disabled=not campi_obbligatori_ok
    ):
        record = {
            "zona_ospedale": zona,
            "setting": setting,
            "auditor": auditor,
            "data_stimata": str(data_stimata),
            "data_effettuazione": str(data_effettuazione),
            "prossimo_audit_proposto": str(nextdate),
            "motivazione_rivalutazione": reason,
            "punteggi_5s": area_scores,
            "totale": total,
            "score_20": score20,
            "risposte": {str(k):v for k,v in answers.items()},
            "osservazioni": {str(k):v for k,v in obs.items()},
        }
        records.append(record)
        save_records(records)
        st.success("Audit salvato nello storico locale.")
        st.rerun()

st.header("Storico degli audit")

if records:
    hist = history_dataframe(records)
    st.dataframe(hist.sort_values(["Data","Audit"], ascending=[False,False]), hide_index=True, use_container_width=True)

    # Gestione storico volutamente subito sotto la tabella, così resta sempre visibile.
    st.subheader("Gestione storico")
    labels = [
        f"{i+1} | {r.get('data_effettuazione','')} | {r.get('zona_ospedale','')} | "
        f"{r.get('setting','')} | {r.get('totale','')}/100"
        for i,r in enumerate(records)
    ]
    selected = st.selectbox(
        "Seleziona un audit da eliminare",
        options=range(len(records)),
        format_func=lambda i: labels[i]
    )
    conferma = st.checkbox("Confermo di voler eliminare l'audit selezionato")
    if st.button("Elimina audit selezionato", disabled=not conferma, use_container_width=True):
        records.pop(selected)
        save_records(records)
        st.success("Audit eliminato.")
        st.rerun()

    # Trend: funziona anche con audit effettuati nella stessa data grazie all'ordine progressivo.
    if zona.strip() and setting.strip():
        trend_records = [
            (i, r) for i, r in enumerate(records)
            if r.get("zona_ospedale","").strip().lower() == zona.strip().lower()
            and r.get("setting","").strip().lower() == setting.strip().lower()
        ]
        if len(trend_records) >= 2:
            trend_records.sort(key=lambda x: (x[1].get("data_effettuazione",""), x[0]))
            xlabels = []
            totals = []
            for pos, (idx, r) in enumerate(trend_records, start=1):
                xlabels.append(f"{r.get('data_effettuazione','')} · #{pos}")
                totals.append(r.get("totale",0))
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=xlabels,
                y=totals,
                mode="lines+markers+text",
                text=[str(v) for v in totals],
                textposition="top center",
                name="Totale /100"
            ))
            fig_trend.update_layout(
                title="Andamento del punteggio complessivo nel tempo",
                yaxis=dict(range=[0,100], title="Punteggio /100"),
                xaxis_title="Audit",
                height=360
            )
            st.plotly_chart(fig_trend, use_container_width=True)

    st.subheader("Esporta dati")
    csv_data = hist.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Scarica storico CSV",
        data=csv_data,
        file_name="storico_audit_5s.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.caption("Il file CSV può essere aperto direttamente con Excel.")
else:
    st.info("Nessun audit salvato: lo storico comparirà dopo il primo salvataggio.")
