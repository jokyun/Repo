`ORA-01745`는 보통 **JSON 자체가 문제라기보다, Oracle이 SQL 안의 어떤 부분을 “bind 변수”로 잘못 해석했을 때** 나는 오류입니다. Oracle 공식 설명도 이 오류를 **“invalid host/bind variable name”**라고 하며, 원인은 `:` 뒤에 부적절한 이름이 왔기 때문이라고 안내합니다. 특히 예약어이거나 bind 변수 이름으로 부적절한 경우가 대표적입니다. ([Oracle Docs][1])

쉽게 말하면, Oracle은 SQL에서 `:name` 같은 형태를 보면 **값을 나중에 넣는 바인드 변수**로 이해합니다. 그런데 JSON을 넣는 과정에서 SQL 안에 `:`가 들어간 부분을 Oracle이나 클라이언트가 bind 변수처럼 해석하면 `ORA-01745`가 발생할 수 있습니다. Oracle의 공식 원인 설명도 정확히 이 패턴입니다. ([Oracle Docs][1])

가장 흔한 원인은 아래 4가지입니다.

첫째, **직접 작성한 SQL에 `:키워드` 형태가 들어간 경우**입니다. 예를 들어 DBeaver에서 이런 식으로 쓰면 문제될 수 있습니다.

```sql
INSERT INTO MY_TABLE (KEYWORDS_JSON)
VALUES ({ "keyword": "oracle", "score": 0.9 });
```

이건 JSON이 문자열로 감싸져 있지 않기 때문에 SQL 문법으로 해석되고, 경우에 따라 `:` 주변을 bind 변수 문맥으로 잘못 보게 됩니다. JSON은 반드시 문자열이나 JSON 타입 값으로 넣어야 합니다.

둘째, **DBeaver가 `:name` 패턴을 파라미터로 처리하는 경우**입니다. 예를 들어 SQL 안에 아래처럼 쓰면:

```sql
INSERT INTO MY_TABLE (KEYWORDS_JSON)
VALUES ('{"type":"news","source":"crawler"}');
```

이 자체는 정상이어야 합니다. 하지만 실제 쿼리를 조합하는 과정에서 문자열 밖에 `:something`이 생기거나, 사용 중인 SQL 템플릿/파라미터 기능 때문에 `:`가 bind 변수처럼 인식되면 같은 오류가 날 수 있습니다. Oracle 쪽에서는 결국 “유효하지 않은 bind 변수 이름”으로 보게 됩니다. ([Oracle Docs][1])

셋째, **bind 변수 이름 자체가 잘못된 경우**입니다. 예를 들어:

```sql
INSERT INTO MY_TABLE (KEYWORDS_JSON)
VALUES (:json-data);
```

이 경우 `json-data`처럼 하이픈이 들어간 이름은 bind 변수명으로 부적절합니다. 또 `:date`, `:number`처럼 상황에 따라 예약어/부적절한 이름으로 해석될 여지도 있습니다. Oracle 공식 문서도 예약어이거나 부적절한 이름일 수 있다고 설명합니다. ([Oracle Docs][1])

넷째, **JSON 저장 방식과 SQL 작성 방식이 섞인 경우**입니다. Oracle에서는 JSON을 보통 `VARCHAR2`, `CLOB`, 또는 버전에 따라 `JSON` 타입 컬럼에 저장합니다. 그런데 JSON 객체를 SQL 안에 “객체처럼” 직접 넣으려 하면 안 되고, 문자열 또는 바인드 값으로 넣어야 합니다. 이때 가장 안전한 방식은 **JSON 전체를 문자열로 넣거나, 파라미터 바인딩으로 넣는 것**입니다.

예를 들어 안전한 예시는 이런 형태입니다.

```sql
INSERT INTO MY_TABLE (ID, KEYWORDS_JSON)
VALUES (
  1,
  '{"keywords":[{"word":"오라클","score":0.98},{"word":"JSON","score":0.87}]}'
);
```

또는 바인드 변수를 쓴다면:

```sql
INSERT INTO MY_TABLE (ID, KEYWORDS_JSON)
VALUES (:id, :keywords_json);
```

이때 `:keywords_json`처럼 **영문자/숫자/언더스코어 중심의 단순한 이름**을 쓰는 편이 안전합니다. Oracle은 bind 변수 이름이 부적절하면 `ORA-01745`를 냅니다. ([Oracle Docs][1])

정리하면, 지금 오류는 대개 아래 중 하나일 가능성이 큽니다.

* JSON을 **문자열로 감싸지 않고** SQL에 직접 넣었다
* SQL 어디엔가 `:무언가` 형태가 생겨서 Oracle이 **bind 변수**로 해석했다
* bind 변수명을 `:json-data`처럼 **잘못 지었다**
* DBeaver에서 실행한 SQL이 내부적으로 파라미터 처리되면서 `:`가 꼬였다

특히 **“크롤링한 데이터를 JSON 형식으로 저장”**하는 상황에서는 JSON 문자열 안의 콜론 자체보다, **SQL 바깥 문맥에서 콜론이 해석되는 것**이 진짜 원인인 경우가 많습니다. 이 부분은 Oracle의 공식 오류 정의와 정확히 맞아떨어집니다. ([Oracle Docs][1])

확인 방법은 간단합니다.

1. JSON을 SQL에 넣을 때 **반드시 작은따옴표로 감싼 문자열**인지 확인
2. SQL 전체에서 `:abc` 같은 패턴이 있는지 확인
3. bind 변수명을 썼다면 `:json_data`, `:p_keywords`처럼 단순한 이름으로 바꾸기
4. 가능하면 JSON 본문을 SQL에 직접 박지 말고 **파라미터 바인딩**으로 넣기

예를 들어 Oracle에서 테이블이 이렇게 있다면:

```sql
CREATE TABLE CRAWLED_KEYWORDS (
  ID NUMBER PRIMARY KEY,
  KEYWORDS_JSON CLOB
);
```

삽입은 이렇게 하는 것이 안전합니다.

```sql
INSERT INTO CRAWLED_KEYWORDS (ID, KEYWORDS_JSON)
VALUES (
  1,
  '{"keywords":["LLM","Oracle","DBeaver"],"source":"crawler"}'
);
```

만약 원하시면 지금 사용 중인 `INSERT` 또는 `UPDATE` 쿼리를 붙여 주시면, **어느 부분에서 ORA-01745가 나는지 정확히 짚어서** 수정본으로 바꿔드리겠습니다.

[1]: https://docs.oracle.com/error-help/db/ora-01745/?utm_source=chatgpt.com "ORA-01745 - Database Error Messages"
