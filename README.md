# Supply Chain Analytics Tool

Aplicație Python / Streamlit pentru analiza ABC–XYZ, stoc de siguranță, punct de reaprovizionare, forecast accuracy și rapoarte Excel.

## Pornire

Python 3.12 recomandat. Din rădăcina proiectului:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py --server.address 0.0.0.0
```

Interfața este în română și pornește cu date demonstrative. Încarcă CSV sau XLSX și descarcă raportul cu patru foi: sursă, analiză SKU, matrice ABC–XYZ, parametri. Nu sunt necesare servicii externe sau credențiale. Datele sunt procesate în memoria procesului; aplicația nu salvează uploadurile pe disc.

## Date

Vezi `data/demo.csv`. Un rând per SKU și lună, fără luni lipsă între prima și ultima observație. Coloane obligatorii: `sku`, `date` (YYYY-MM-DD), `demand`, `unit_cost`, `lead_time_days`; opțional `forecast`. Numere finite ≥ 0. Costul unitar și lead time sunt constante per SKU. Folosește aceeași monedă și același interval de observație pentru toate SKU-urile. Istoricul trebuie să includă explicit lunile cu cerere zero.

ABC folosește valoarea consumului pe întreg intervalul, cu praguri implicite 80% / 95%; produsul care traversează pragul rămâne în clasa începută. Valoarea zero primește N/A. XYZ folosește coeficientul de variație eșantion (praguri 0.5 / 1.0). Medie zero sau istoric sub două luni → N/A.

Safety stock = z × σ lunar × √(lead time / 30). Reorder point = media lunară × lead time / 30 + safety stock. Modelul presupune cerere independentă aproximativ normală, luni de 30 zile și lead time fix; nu modelează sezonalitate sau incertitudinea lead time. Nivelul de serviciu este probabilitatea evitării rupturii într-un ciclu. Rezultatele sunt cantități continue, de adaptat la ambalaje. Nu se generează prognoze: se evaluează coloana `forecast` furnizată.

MAE și RMSE sunt exprimate în unități; MAPE și WAPE în procente. MAPE exclude cererea zero și raportează numărul de luni eligibile; WAPE folosește toate erorile absolute / cererea totală. Numitor zero → N/A. Bias = media(prognoză − cerere), pozitiv pentru supraestimare. Indicatorii sunt calculați per SKU.

## Verificare

```bash
python -m unittest discover -s tests -v
```

Testele verifică formulele, cazurile de cerere zero, validarea datelor, pragurile ABC și exportul Excel. Metodologia este disponibilă și în aplicație. XLSX folosește prima foaie la import; CSV folosește separatorul virgulă și punctul zecimal.
