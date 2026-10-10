"""Creates the doctors' extra data files. Additive only: no existing file is read for writing or changed.
Every row carries a `source` of persona_document (stated in Realistic_Persona_Meera.md) or
synthetic_best_guess_v1 (invented here, awaiting a doctor's review)."""
import pandas as pd, numpy as np, json, math, os
OUT=os.path.dirname(os.path.abspath(__file__)); DS="/mnt/user-data/outputs/final_dataset/"
PID="meera_iyer_v1"; DOB=pd.Timestamp("1983-04-12")
PER="persona_document"; GUESS="synthetic_best_guess_v1"
def age(d): d=pd.Timestamp(d); return d.year-DOB.year-((d.month,d.day)<(DOB.month,DOB.day))
def ckdepi(scr,a):  # CKD-EPI 2021, female
    return 142*min(scr/0.7,1)**-0.241*max(scr/0.7,1)**-1.200*0.9938**a*1.012
def wcsv(df,name): df.to_csv(os.path.join(OUT,name),index=False,lineterminator="\r\n")
# ---------------- CGM (Baseline cleaning rule) for fructosamine anchors and HSI BMI lookups
g=pd.read_csv(DS+"glucose_stream_yearly.csv"); g["ts"]=pd.to_datetime(g["timestamp"].astype(str).str[:19]); g["v"]=pd.to_numeric(g["value"],errors="coerce"); g=g.sort_values("ts")
kept=[]; last=None
for ts,v in zip(g["ts"],g["v"]):
    if not(40<=v<=400): continue
    if last is not None and abs(v-last)>75: continue
    kept.append((ts,v)); last=v
cgm=pd.DataFrame(kept,columns=["ts","v"])
def gmi90(d):
    e=pd.Timestamp(d); w=cgm[(cgm["ts"]>=e-pd.Timedelta(days=90))&(cgm["ts"]<e)]["v"]
    return round(3.31+0.02392*w.mean(),2) if len(w)>1000 else None
wt=pd.read_csv(DS+"weight_yearly.csv"); wt["d"]=pd.to_datetime(wt["timestamp"].astype(str).str[:10]); wt=wt.set_index("d")["value"].astype(float)
def nearest_weight(d):
    d=pd.Timestamp(d); i=int(np.argmin(np.abs((wt.index-d).days))); return float(wt.iloc[i])
# =============== 1. labs history (before the data year) =============================
VISITS=["2021-10-12","2022-02-04","2022-05-12","2022-09-20","2023-01-20","2023-06-12","2023-10-04","2024-03-14","2024-09-24","2025-03-11","2025-06-17"]
H={ # per visit: dict of type -> value (types absent = not measured at that visit)
"2021-10-12":dict(tsh=7.6,total_cholesterol=208,ldl_c=130,hdl_c=49,triglycerides=145,creatinine=0.8,alt=28,ast=24,ggt=30),
"2022-02-04":dict(fasting_glucose=162,hba1c=8.0,total_cholesterol=222,ldl_c=140,hdl_c=44,triglycerides=190,creatinine=0.8,alt=38,ast=30,ggt=40,tsh=4.2,uacr=18),
"2022-05-12":dict(fasting_glucose=128,hba1c=7.1,tsh=3.4),
"2022-09-20":dict(fasting_glucose=132,hba1c=7.2,tsh=3.2),
"2023-01-20":dict(fasting_glucose=136,hba1c=7.3,total_cholesterol=214,ldl_c=128,hdl_c=45,triglycerides=178,creatinine=0.8,alt=40,ast=31,ggt=42,tsh=3.0,uacr=20),
"2023-06-12":dict(fasting_glucose=148,hba1c=7.8,creatinine=0.9,tsh=3.3),
"2023-10-04":dict(fasting_glucose=130,hba1c=7.2,total_cholesterol=208,ldl_c=124,hdl_c=46,triglycerides=172,creatinine=0.8,tsh=3.1),
"2024-03-14":dict(fasting_glucose=126,hba1c=7.0,creatinine=0.8,alt=41,ast=31,ggt=44,tsh=2.8,uacr=16),
"2024-09-24":dict(fasting_glucose=138,hba1c=7.4,total_cholesterol=210,ldl_c=128,hdl_c=45,triglycerides=182,creatinine=0.8,tsh=2.9),
"2025-03-11":dict(fasting_glucose=134,hba1c=7.2,total_cholesterol=206,ldl_c=126,hdl_c=46,triglycerides=176,creatinine=0.8,alt=44,ast=33,ggt=47,tsh=3.2,uacr=12),
"2025-06-17":dict(fasting_glucose=135,hba1c=7.2,creatinine=0.8,alt=46,ast=34,ggt=52,tsh=3.1),
}
UNIT=dict(fasting_glucose="mg/dL",hba1c="%",total_cholesterol="mg/dL",ldl_c="mg/dL",hdl_c="mg/dL",triglycerides="mg/dL",creatinine="mg/dL",egfr="mL/min/1.73m2",alt="U/L",ast="U/L",ggt="U/L",tsh="mIU/L",uacr="mg/g",apob="mg/dL",lp_a="nmol/L",fasting_insulin="uU/mL",homa_ir="index",fructosamine="umol/L",hsi="index")
ORDER=["fasting_glucose","hba1c","total_cholesterol","ldl_c","hdl_c","triglycerides","creatinine","egfr","alt","ast","ggt","tsh","uacr"]
rows=[]; n=0
for d in VISITS:
    vals=dict(H[d])
    if "creatinine" in vals: vals["egfr"]=round(ckdepi(vals["creatinine"],age(d)),1)
    for t in ORDER:
        if t in vals:
            n+=1; rows.append(dict(event_id=f"labh_{n:03d}",patient_id=PID,timestamp=f"{d}T08:00:00+05:30",type=t,value=vals[t],unit=UNIT[t],source=GUESS+" (anchors from persona)"))
LH=pd.DataFrame(rows); wcsv(LH,"labs_history_2021_2025.csv")
# =============== 2. additional tests on the data year ================================
DATES=["2025-09-15","2025-12-18","2026-03-06","2026-06-17","2026-09-17"]
FPG={"2025-09-15":132,"2025-12-18":145,"2026-03-06":128,"2026-06-17":131,"2026-09-17":138}
TC={"2025-09-15":205,"2025-12-18":212,"2026-03-06":198,"2026-06-17":202,"2026-09-17":206}
HDL={"2025-09-15":46,"2025-12-18":44,"2026-03-06":47,"2026-06-17":46,"2026-09-17":45}
INS={"2025-09-15":14.0,"2025-12-18":17.0,"2026-03-06":12.5,"2026-06-17":13.5,"2026-09-17":15.0}
rows=[]; n=0
def add(d,t,v,src=GUESS):
    global n; n+=1; rows.append(dict(event_id=f"laba_{n:03d}",patient_id=PID,timestamp=f"{d}T08:00:00+05:30",type=t,value=v,unit=UNIT[t],source=src))
# the interim mid-year panel (new date): the persona's 'one mildly out-of-range TSH mid-year' and the missing quarterly panel
for t,v in [("fasting_glucose",131),("hba1c",7.2),("total_cholesterol",202),("ldl_c",122),("hdl_c",46),("triglycerides",170),("creatinine",0.8),("egfr",93.7),("alt",41),("ast",31),("ggt",45),("tsh",4.7)]:
    add("2026-06-17",t,v)
# hepatic steatosis index for the new panel: 8 x ALT/AST + BMI + 2 (diabetes) + 2 (female)
bmi_j=round(nearest_weight("2026-06-17")/1.6**2,2); add("2026-06-17","hsi",round(8*41/31+bmi_j+4,1))
for d in DATES:
    nonhdl=TC[d]-HDL[d]; add(d,"apob",round(0.63*nonhdl))
    add(d,"fasting_insulin",INS[d]); add(d,"homa_ir",round(INS[d]*FPG[d]/405,2))
    gm=gmi90(d); f=round((gm-1.61)/0.017) if gm else 287   # concordant with the CGM; 2025-09-15 has no CGM before it
    add(d,"fructosamine",f)
add("2025-09-15","uacr",14); add("2026-09-17","uacr",18); add("2026-03-06","lp_a",48)
LA=pd.DataFrame(rows).sort_values(["timestamp","type"]).reset_index(drop=True); LA["event_id"]=[f"laba_{i+1:03d}" for i in range(len(LA))]; wcsv(LA,"labs_additional_2025_2026.csv")
# =============== 3. anthropometry history =============================================
AW={"2021-10-12":(68.8,85.2,101.8),"2022-02-04":(69.5,86.0,102.2),"2022-05-12":(69.0,85.6,102.0),"2022-09-20":(68.9,85.8,102.1),"2023-01-20":(69.8,86.4,102.6),"2023-06-12":(70.6,87.0,103.0),"2023-10-04":(70.2,86.6,102.8),"2024-03-14":(69.7,86.2,102.6),"2024-09-24":(70.4,87.0,103.0),"2025-03-11":(70.8,87.6,103.4),"2025-06-17":(71.0,88.2,103.6)}
rows=[dict(patient_id=PID,date=d,weight_kg=w,height_cm=160,bmi=round(w/1.6**2,2),waist_cm=wa,hip_cm=hi,whr=round(wa/hi,3),whtr=round(wa/160,3),source=GUESS+" (anchors from persona)") for d,(w,wa,hi) in AW.items()]
AH=pd.DataFrame(rows); wcsv(AH,"anthropometry_history.csv")
# =============== 4. clinic blood pressure history =====================================
BP=[("2021-10-12",126,80),("2022-02-04",130,84),("2022-05-12",128,82),("2022-09-20",132,84),("2022-12-09",142,92),("2023-01-20",144,94),("2023-02-24",134,86),("2023-06-12",132,84),("2023-10-04",130,82),("2024-03-14",128,82),("2024-09-24",132,84),("2025-03-11",130,84),("2025-06-17",132,86)]
vt=pd.read_csv(DS+"vitals_yearly.csv"); vt["d"]=pd.to_datetime(vt["timestamp"].astype(str).str[:10]); bpd=vt[vt["type"]=="blood_pressure"].set_index("d")["value"]
for d in DATES:  # clinic readings on the data-year visit dates (clinic reading, a little above the home median)
    BP.append((d,{"2025-09-15":(132,84),"2025-12-18":(136,88),"2026-03-06":(128,82),"2026-06-17":(130,82),"2026-09-17":(138,90)}[d][0],{"2025-09-15":(132,84),"2025-12-18":(136,88),"2026-03-06":(128,82),"2026-06-17":(130,82),"2026-09-17":(138,90)}[d][1]))
rows=[dict(patient_id=PID,date=d,systolic=s,diastolic=di,position="seated",measured_by="clinic",source=GUESS+(" (2022-12-09 and 2023-01-20 anchor the 2023 hypertension diagnosis)" if d in("2022-12-09","2023-01-20") else "")) for d,s,di in sorted(BP)]
BH=pd.DataFrame(rows); wcsv(BH,"bp_clinic_history.csv")
# =============== 5. imaging ===========================================================
ctx=vt[vt["context"].notna()][["timestamp","type","value","context"]]
ecg_date=str(ctx.iloc[0]["timestamp"])[:10] if len(ctx) else "2026-04-06"
IM=pd.DataFrame([
 dict(patient_id=PID,date="2025-06-17",modality="Abdominal ultrasound",indication="Persistently mildly raised ALT and GGT in type 2 diabetes with overweight",finding="Mild (grade 1) diffuse increase in liver echogenicity consistent with hepatic steatosis; no focal lesion; spleen, kidneys and pancreas unremarkable",grade="1 of 3",impression="Hepatic steatosis; with type 2 diabetes and overweight this meets the NMG Lite working definition of MASLD; alcohol occasional (1 to 2 times a month)",source=GUESS),
 dict(patient_id=PID,date=ecg_date,modality="12-lead ECG",indication="Walk-in consultation with elevated heart rate noted (existing vitals note)",finding="Normal sinus rhythm",grade="",impression="Normal ECG",source="vitals_yearly.csv context note + "+GUESS)]); wcsv(IM,"imaging_reports.csv")
# =============== 6. IPAQ-Short quarterly =============================================
IP=[("2025-09-30",0,0,1,20,4,15,9.0),("2025-12-31",0,0,1,15,4,15,9.5),("2026-03-31",0,0,0,0,3,15,10.0),("2026-06-30",0,0,2,20,5,20,9.0),("2026-09-17",0,0,1,15,4,15,9.5)]
rows=[]
for d,vd,vm,md,mm,wd,wm,sit in IP:
    mv,mo,mw=8.0*vm*vd,4.0*mm*md,3.3*wm*wd; tot=mv+mo+mw
    act_days=vd+md+wd
    high=(vd>=3 and mv>=1500) or (vd+md+wd>=7 and tot>=3000)
    mod=(vd>=3 and vm>=20) or ((md>=5 or wd>=5) and (mm>=30 or wm>=30)) or (act_days>=5 and tot>=600)
    cat="high" if high else ("moderate" if mod else "low")
    rows.append(dict(patient_id=PID,date=d,vigorous_days=vd,vigorous_min_per_day=vm,moderate_days=md,moderate_min_per_day=mm,walking_days=wd,walking_min_per_day=wm,sitting_hours_weekday=sit,met_min_week_vigorous=mv,met_min_week_moderate=mo,met_min_week_walking=round(mw,1),met_min_week_total=round(tot,1),category=cat,source=GUESS+" (consistent with the steps and sedentary files)"))
IPD=pd.DataFrame(rows); wcsv(IPD,"ipaq_short_quarterly.csv")
# =============== 7. standing records ==================================================
C=[
("Type 2 diabetes mellitus","active","2022-02-04","persona_stated","Oral therapy; dose adjusted once on 2023-06-15; second agent considered but not started",PER),
("Hypertension (moderate)","active, medicated","2023-01-20","year stated (2023); day is a best guess","Amlodipine 5 mg daily from the same date",PER+" (year); "+GUESS+" (day)"),
("Subclinical hypothyroidism","active, managed","2021-10-12","year stated (2021); day is a best guess","Levothyroxine 50 mcg daily from 2021-11-01; pre-dates the diabetes",PER+" (year); "+GUESS+" (day)"),
("Mild anxiety","self-reported, intermittent","","not dated","Not formally diagnosed; worse in caregiving-heavy or work-heavy stretches",PER),
("Perimenopause","active","2025-02-01","approximate (persona: early 2025)","Irregular cycles of 24 to 45 days; some anovulatory months",PER),
("Dyslipidemia (high triglycerides, low HDL-C)","active, untreated","2022-02-04","derived from the first panel at diagnosis","TG 190 and HDL-C 44 mg/dL at diagnosis; no lipid-lowering therapy",GUESS+" (derived from labs)"),
("Obesity (BMI 25 or more, ICMR-INDIAB definition)","active","2022-02-04","derived from anthropometry","BMI 27.1 at diagnosis, 28.2 at the reference date",GUESS+" (derived from anthropometry)"),
("Hepatic steatosis / MASLD","active","2025-06-17","ultrasound date","Grade 1 steatosis on ultrasound; type 2 diabetes and overweight; occasional alcohol",GUESS),
("Atherosclerotic cardiovascular disease","none documented","","","Persona lists no cardiovascular disease for her",GUESS+" (persona silent)"),
("Heart failure","none documented","","","",GUESS+" (persona silent)"),
("Chronic kidney disease","none documented","","","eGFR 93.7 and UACR under 30 mg/g; no kidney damage marker",GUESS+" (derived from labs)"),
("Polycystic ovary syndrome","none documented","","","Not in the persona's comorbidity list; irregular cycles are attributed to perimenopause",GUESS+" (persona silent)"),
("Gestational diabetes (history)","none documented","","","Two children, ages 12 and 15; no complications recorded",GUESS+" (persona silent)"),
("Retinopathy, neuropathy, nephropathy","none documented","","","No complication recorded",GUESS+" (persona silent)"),
]
CD=pd.DataFrame([dict(patient_id=PID,condition=a,status=b,diagnosed_date=c,date_basis=d,note=e,source=f) for a,b,c,d,e,f in C]); wcsv(CD,"conditions_standing_record.csv")
MD=pd.DataFrame([
 dict(patient_id=PID,medication="Levothyroxine",indication="Subclinical hypothyroidism",dose="50 mcg",frequency="once daily",start_date="2021-11-01",end_date="",status="active",data_adherence_id="med_004_levothyroxine",source=PER),
 dict(patient_id=PID,medication="Metformin",indication="Type 2 diabetes",dose="500 mg",frequency="twice daily",start_date="2022-02-10",end_date="2023-06-14",status="superseded by the higher dose",data_adherence_id="(unused id med_001, to confirm)",source=PER),
 dict(patient_id=PID,medication="Amlodipine",indication="Hypertension",dose="5 mg",frequency="once daily",start_date="2023-01-20",end_date="",status="active",data_adherence_id="med_003_amlodipine",source=PER),
 dict(patient_id=PID,medication="Metformin",indication="Type 2 diabetes",dose="1000 mg",frequency="twice daily",start_date="2023-06-15",end_date="",status="active",data_adherence_id="med_002_metformin",source=PER+" (dose raised after a suboptimal HbA1c)"),
 dict(patient_id=PID,medication="Lipid-lowering therapy",indication="",dose="",frequency="",start_date="",end_date="",status="none",data_adherence_id="",source=GUESS+" (persona silent)"),
 dict(patient_id=PID,medication="Glucocorticoids and other metabolically relevant drugs",indication="",dose="",frequency="",start_date="",end_date="",status="none",data_adherence_id="",source=GUESS+" (persona silent)"),
 dict(patient_id=PID,medication="Second glucose-lowering agent",indication="Type 2 diabetes",dose="",frequency="",start_date="",end_date="",status="considered, not started (persona: borderline candidate)",data_adherence_id="",source=PER)]); wcsv(MD,"medications_history.csv")
FH=pd.DataFrame([
 dict(patient_id=PID,relative="Mother",degree="first",condition="Type 2 diabetes",age_at_onset=58,event_year=2016,premature="not applicable",source=PER+" (onset age); "+GUESS+" (year)"),
 dict(patient_id=PID,relative="Father",degree="first",condition="Hypertension",age_at_onset=52,event_year=2007,premature="not applicable",source=PER+" (condition); "+GUESS+" (age)"),
 dict(patient_id=PID,relative="Father",degree="first",condition="Coronary artery disease with bypass surgery",age_at_onset=64,event_year=2019,premature="no (male relative; premature means under 55)",source=PER+" (condition and year); "+GUESS+" (his age, so not premature)"),
 dict(patient_id=PID,relative="Mother",degree="first",condition="Cardiovascular disease",age_at_onset="",event_year="",premature="not documented",source=GUESS+" (persona silent)"),
 dict(patient_id=PID,relative="Any first-degree relative",degree="first",condition="PCOS",age_at_onset="",event_year="",premature="not documented",source=GUESS+" (persona silent)"),
 dict(patient_id=PID,relative="Any first-degree relative",degree="first",condition="Gestational diabetes",age_at_onset="",event_year="",premature="not documented",source=GUESS+" (persona silent)"),
 dict(patient_id=PID,relative="Any first-degree relative",degree="first",condition="Known inherited or genetic condition",age_at_onset="",event_year="",premature="not documented",source=GUESS+" (persona silent)")]); wcsv(FH,"family_history_standing_record.csv")
LS=pd.DataFrame([
 dict(patient_id=PID,domain="Tobacco",value="never smoker",detail="No smoking",as_of_date="2026-09-17",source=PER),
 dict(patient_id=PID,domain="Alcohol",value="occasional, social",detail="Wine or beer about 1 to 2 times a month, slightly more in stressful periods; 6 diary entries in the data year (25 Dec to 14 Feb)",as_of_date="2026-09-17",source=PER),
 dict(patient_id=PID,domain="Caffeine",value="3 to 4 cups a day in stressful periods",detail="Occasional dependency",as_of_date="2026-09-17",source=PER),
 dict(patient_id=PID,domain="Other substances",value="none",detail="",as_of_date="2026-09-17",source=GUESS+" (persona silent)"),
 dict(patient_id=PID,domain="Occupation",value="Finance Manager, mid-size manufacturing company",detail="Full-time; high-pressure quarter-end cycles; moderate travel (2 to 3 trips a quarter)",as_of_date="2026-09-17",source=PER),
 dict(patient_id=PID,domain="Occupational pattern flag",value="adverse",detail="Quarter-end deadlines, travel, long screen time (7 to 9 hours a day)",as_of_date="2026-09-17",source=PER+" (pattern); "+GUESS+" (flag)"),
 dict(patient_id=PID,domain="Household",value="Married, two children (12 and 15); ageing parents nearby with occasional caregiving",detail="Primary logistical load falls on her",as_of_date="2026-09-17",source=PER),
 dict(patient_id=PID,domain="Diet pattern",value="irregular timing",detail="Breakfast often skipped or rushed; canteen or delivery lunch on office days; dinner about 7 pm on calm days and 9:30 to 10 pm in crunch periods; occasional overeating at social events",as_of_date="2026-09-17",source=PER),
 dict(patient_id=PID,domain="Sleep source",value="wearable (synthetic)",detail="Average of the prior 7 nights should name this source",as_of_date="2026-09-17",source=GUESS),
 dict(patient_id=PID,domain="Physical activity",value="low, irregular",detail="See ipaq_short_quarterly.csv; wearable median 2,106 steps a day",as_of_date="2026-09-17",source=GUESS+" (consistent with the wearable data)")]); wcsv(LS,"lifestyle_standing_record.csv")
GL=pd.DataFrame([
 dict(patient_id=PID,goal_domain="HbA1c",target="under 7.0 %",rationale="Individualized ADA goal for a non-pregnant adult at low hypoglycemia risk on metformin",set_by="clinic (best guess)",set_date="2022-05-12",source=GUESS+" (doctor to confirm)"),
 dict(patient_id=PID,goal_domain="LDL-C",target="under 70 mg/dL",rationale="ADA 2026 as quoted in NMG Lite: diabetes aged 40 to 75 at higher cardiovascular risk (diabetes, treated hypertension, central adiposity, father with coronary disease)",set_by="clinic (best guess)",set_date="2025-03-11",source=GUESS+" (doctor to confirm)"),
 dict(patient_id=PID,goal_domain="Blood pressure",target="under 130/80 mmHg",rationale="Common target for diabetes with hypertension; not stated in NMG Lite",set_by="clinic (best guess)",set_date="2023-01-20",source=GUESS+" (doctor to confirm)"),
 dict(patient_id=PID,goal_domain="Triglycerides",target="under 150 mg/dL",rationale="NMG Lite Green band",set_by="NMG Lite",set_date="",source=GUESS+" (taken from the band)"),
 dict(patient_id=PID,goal_domain="TG/HDL-C",target="under 2.0",rationale="NMG Lite Green band (operational, not a validated cutoff)",set_by="NMG Lite",set_date="",source=GUESS+" (taken from the band)"),
 dict(patient_id=PID,goal_domain="Sleep",target="at least 7 hours a night",rationale="AASM and SRS consensus, as cited in NMG Lite",set_by="NMG Lite",set_date="",source=GUESS+" (taken from the band)"),
 dict(patient_id=PID,goal_domain="Physical activity",target="IPAQ moderate category or higher",rationale="NMG Lite Green band",set_by="NMG Lite",set_date="",source=GUESS+" (taken from the band)"),
 dict(patient_id=PID,goal_domain="Weight",target="reduce about 5 % (to about 68 kg) over 12 months",rationale="Common goal for diabetes with overweight; not in NMG Lite",set_by="clinic (best guess)",set_date="2025-03-11",source=GUESS+" (doctor to confirm)"),
 dict(patient_id=PID,goal_domain="Kidney monitoring",target="eGFR and UACR at least yearly",rationale="ADA 2026 as quoted in NMG Lite section 5",set_by="NMG Lite",set_date="",source=GUESS+" (taken from the document)")]); wcsv(GL,"treatment_goals_standing_record.csv")
# =============== 8. clinic visits =====================================================
def hb(d): 
    x=H.get(d,{}).get("hba1c"); return x
VD=[("2021-10-12","routine","Fatigue and a thyroid work-up","", "Subclinical hypothyroidism found (TSH 7.6). Levothyroxine 50 mcg to start on 2021-11-01"),
("2022-02-04","diagnosis","Routine check after unexplained fatigue; family history of diabetes","8.0","Type 2 diabetes diagnosed. Metformin 500 mg twice daily to start on 2022-02-10; diet and activity advice"),
("2022-05-12","follow-up","Three months on metformin","7.1","Continue; recheck in 4 months"),
("2022-09-20","follow-up","Routine","7.2","Continue; recheck in 4 months"),
("2022-12-09","acute","Headache; blood pressure 142/92","","Home blood pressure monitoring advised"),
("2023-01-20","follow-up","Raised blood pressure on two visits","7.3","Hypertension diagnosed. Amlodipine 5 mg daily started"),
("2023-06-12","follow-up","Suboptimal HbA1c","7.8","Metformin raised to 1000 mg twice daily on 2023-06-15"),
("2023-10-04","follow-up","Three months after the dose increase","7.2","Continue"),
("2024-03-14","follow-up","Routine","7.0","Continue"),
("2024-09-24","follow-up","Routine","7.4","Continue; lifestyle counselling"),
("2025-03-11","follow-up","Irregular cycles; perimenopause discussed","7.2","Continue; ALT and GGT mildly raised; recheck"),
("2025-06-17","follow-up","Persistently mildly raised ALT and GGT","7.2","Abdominal ultrasound ordered: grade 1 hepatic steatosis"),
("2025-09-15","quarterly review","Routine","7.1","Continue"),
("2025-12-18","quarterly review","Holiday-season rise in glucose","7.6","Counselling on diet and activity; recheck in 3 months"),
("2026-03-06","quarterly review","After the New Year effort","7.0","Continue"),
("2026-06-17","interim review","Mid-year review; TSH slightly above range","7.2","Levothyroxine unchanged; repeat TSH in 6 to 8 weeks"),
("2026-09-17","quarterly review","HbA1c back up to 7.4","7.4","Second agent discussed and deferred; three more months of lifestyle effort")]
rows=[]
for d,vt_,reason,h,dec in VD:
    w=AW[d][0] if d in AW else nearest_weight(d)
    if d=="2025-09-15": w=71.0
    bpv=[(s,di) for dd,s,di in BP if dd==d]; bps=f"{bpv[0][0]}/{bpv[0][1]}" if bpv else ""
    rows.append(dict(patient_id=PID,visit_date=d,visit_type=vt_,reason=reason,hba1c_percent=h,weight_kg=w,clinic_bp=bps,key_decision=dec,source=GUESS+" (anchors from persona)"))
VH=pd.DataFrame(rows); wcsv(VH,"clinic_visits_history.csv")
print({f:len(pd.read_csv(os.path.join(OUT,f))) for f in sorted(os.listdir(OUT)) if f.endswith(".csv")})
