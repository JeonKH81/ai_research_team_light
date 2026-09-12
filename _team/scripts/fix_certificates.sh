#!/bin/zsh
# 파이썬이 바깥 자료를 못 받아올 때 — 맥이 믿는 신분증을 파이썬에게 준다.
#
#   zsh "_team/scripts/fix_certificates.sh"
#
# ## 무슨 문제인가
#
# 2026-09-06 맥미니의 문헌 수집이 이렇게 실패했다:
#
#   eutils.ncbi.nlm.nih.gov  SSL: CERTIFICATE_VERIFY_FAILED
#                            self-signed certificate in certificate chain
#
# 통신이 막힌 것이 아니다. 중간에 있는 장비가 통신을 열어 보고 **자기 신분증으로 다시 봉해서**
# 보낸다. 맥은 그 장비를 이미 믿고 있어서 사파리도 Claude도 잘 된다 —
# 그 신분증이 맥의 꾸러미에 들어 있기 때문이다.
#
# 그런데 파이썬은 맥의 꾸러미를 보지 않고 자기 것(certifi)만 본다. 거기에는 없다.
# `pip install --upgrade certifi` 로는 고쳐지지 않는다. 공인된 신분증만 담기기 때문이다.
#
# ## 무엇을 하는가
#
# 맥의 꾸러미 셋(시스템 기본·기관 추가분·사용자 추가분)을 꺼내 한 파일로 합치고,
# 저절로 도는 작업들이 그것을 쓰도록 한다. **관리자 권한이 필요 없다.** 읽어서 옮겨 담을 뿐이다.
#
# 기관이 신분증을 바꾸면 다시 실행하면 된다.

set -e
OUT="$HOME/.config/lab-ca.pem"
mkdir -p "$(dirname "$OUT")"
TMP="$OUT.tmp.$$"

echo "맥이 믿는 신분증을 모읍니다 — $(hostname -s)"
echo

: > "$TMP"
for K in "/System/Library/Keychains/SystemRootCertificates.keychain" \
         "/Library/Keychains/System.keychain" \
         "$HOME/Library/Keychains/login.keychain-db"; do
  [[ -e "$K" ]] || continue
  N=$(security find-certificate -a -p "$K" 2>/dev/null | tee -a "$TMP" | grep -c "BEGIN CERTIFICATE" || true)
  printf "  %-46s %3s개\n" "$(basename "$K")" "${N:-0}"
done

TOTAL=$(grep -c "BEGIN CERTIFICATE" "$TMP" || true)
if [[ "${TOTAL:-0}" -lt 50 ]]; then
  rm -f "$TMP"
  echo
  echo "✗ 신분증이 너무 적게 나왔습니다(${TOTAL:-0}개). 무언가 잘못됐으니 그대로 두겠습니다."
  exit 1
fi
mv "$TMP" "$OUT"
echo
echo "  합쳐서 ${TOTAL}개 → $OUT"

echo
echo "이 꾸러미로 실제로 닿는지 확인합니다."
if SSL_CERT_FILE="$OUT" python3 - <<'PY'
import urllib.request, json, sys
ok = 0
for name, u in (("PubMed", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&retmax=0&term=statin"),
                ("medRxiv", "https://api.biorxiv.org/details/medrxiv/10.1101/2020.01.01.20016915")):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "lab/1.0"}), timeout=30) as r:
            r.read(200); print("  %-10s 닿음" % name); ok += 1
    except Exception as e:
        print("  %-10s 실패 — %s" % (name, str(e)[:70]))
sys.exit(0 if ok else 1)
PY
then
  echo
  echo "됐습니다. 저절로 도는 작업들이 이 꾸러미를 쓰도록 이미 되어 있습니다."
  echo "내일 새벽 05:45 문헌 수집부터 정상으로 돌아옵니다."
else
  echo
  echo "아직 닿지 않습니다. 다른 원인일 수 있으니 위 오류 문구를 알려주십시오."
  exit 1
fi
