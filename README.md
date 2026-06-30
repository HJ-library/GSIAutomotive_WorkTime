# GSIAutomotive_WorkTime

GSI Automotive 근태 관리 데스크톱 툴입니다.

## 실행

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

기존 개발 환경에서는 `run.bat`으로 실행할 수 있습니다.

## 테스트

```bat
python -m unittest
```

## 패키징

```bat
pyinstaller WorkTimeManager.spec
```
