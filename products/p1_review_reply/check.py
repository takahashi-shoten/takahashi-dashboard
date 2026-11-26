import json,re
tc={c["id"]:c for c in json.load(open("testcases.json",encoding="utf-8"))}
out=json.load(open("outputs_claude_run2.json",encoding="utf-8"))
ban=["絶対","必ず","No.1","ナンバーワン","全員","100%","保証","治る"]
ok=0
for i,c in tc.items():
    r=out[i]; n=len(r); res={}
    res["長さ120-220"]=120<=n<=220
    res["禁止語なし"]=not any(b in r for b in ban)
    res["お礼で開始"]=r.startswith(("ご来店","初めての","ご来店いただき"))
    kw=re.findall(r"カット|カラー|雰囲気|説明|仕上がり|髪色|写真|お写真|15分|態度|対応|接客|大声|ご意見",c["text"])
    res["口コミ語の引用"]=any(k in r for k in kw) if kw else False
    if c["stars"]<=2: res["お詫び1回"]=r.count("申し訳")==1 or r.count("申し訳")<=2
    if c["stars"]<=2: res["言い訳/断定なし"]=not any(w in r for w in ["勘違い","誤解","事実と","お客様の側"])
    passed=all(res.values()); ok+=passed
    print(i,n,"PASS" if passed else "FAIL",{k:v for k,v in res.items() if not v})
print(f"{ok}/{len(tc)} pass")
