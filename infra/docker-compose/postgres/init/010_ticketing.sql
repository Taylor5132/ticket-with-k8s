--
-- PostgreSQL database dump
--

\restrict O3ZcvpiGXy25D6gDTu2RbHXBBNwmSXdhWMIAN9JhARKaH2iTjR5gZohjQ0bspXl

-- Dumped from database version 18.4
-- Dumped by pg_dump version 18.4

-- Started on 2026-06-09 18:50:44

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 222 (class 1259 OID 16432)
-- Name: performances; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.performances (
    id integer NOT NULL,
    kopis_id character varying(20),
    venue_id integer,
    title character varying(500),
    start_date date,
    end_date date,
    poster_url text,
    genre character varying(100),
    status character varying(20),
    is_open_run character(1),
    cast_text text,
    runtime character varying(50),
    age_rating character varying(50),
    description text,
    intro_image_urls text,
    schedule text
);


ALTER TABLE public.performances OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 16431)
-- Name: performances_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.performances_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.performances_id_seq OWNER TO postgres;

--
-- TOC entry 4927 (class 0 OID 0)
-- Dependencies: 221
-- Name: performances_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.performances_id_seq OWNED BY public.performances.id;


--
-- TOC entry 220 (class 1259 OID 16420)
-- Name: venues; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.venues (
    id integer NOT NULL,
    kopis_id character varying(20),
    name character varying(255),
    address text,
    province character varying(50),
    district character varying(50),
    seat_capacity integer,
    phone character varying(20),
    latitude numeric(18,14),
    longitude numeric(18,14),
    halls_text text
);


ALTER TABLE public.venues OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 16419)
-- Name: venues_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.venues_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.venues_id_seq OWNER TO postgres;

--
-- TOC entry 4928 (class 0 OID 0)
-- Dependencies: 219
-- Name: venues_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.venues_id_seq OWNED BY public.venues.id;


--
-- TOC entry 4761 (class 2604 OID 16435)
-- Name: performances id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.performances ALTER COLUMN id SET DEFAULT nextval('public.performances_id_seq'::regclass);


--
-- TOC entry 4760 (class 2604 OID 16423)
-- Name: venues id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.venues ALTER COLUMN id SET DEFAULT nextval('public.venues_id_seq'::regclass);


--
-- TOC entry 4921 (class 0 OID 16432)
-- Dependencies: 222
-- Data for Name: performances; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.performances (id, kopis_id, venue_id, title, start_date, end_date, poster_url, genre, status, is_open_run, cast_text, runtime, age_rating, description, intro_image_urls, schedule) FROM stdin;
1	PF293159	1	이수민 바이올린 독주회: 바이올린 선율의 판타지 Ⅱ	2026-06-28	2026-06-28	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293159_260608_170502.png	서양음악(클래식)	공연예정	N	이수민, 방선혜	1시간 30분	만 4세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293159_202606080505025971.png|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293159_202606080505025870.png	일요일(14:00)
2	PF293158	1	이수민 바이올린 독주회: 바이올린 선율의 판타지 Ⅰ	2026-06-14	2026-06-14	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293158_260608_170029.png	서양음악(클래식)	공연예정	N	이수민, 박희민	1시간 30분	만 4세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293158_202606080500292431.png|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293158_202606080500292120.png	일요일(14:00)
3	PF293157	2	이선아 피아노 독주회: J.S.Bach Keyboard Suite 전곡 시리즈 Ⅲ	2026-07-05	2026-07-05	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293157_260608_165513.gif	서양음악(클래식)	공연예정	N	이선아	1시간 30분	만 7세 이상	[PROGRAM]                                     J.S.Bach (1685-1750) French Suite No.3 in B Minor, BWV 814 Partita No.4 in D Major, BWV 828 French Overture in B Minor, BWV 831	http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293157_202606080455131880.jpg	일요일(14:00)
4	PF293153	3	윤수정 피아노 독주회	2026-06-15	2026-06-15	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293153_260608_164224.gif	서양음악(클래식)	공연예정	N	윤수정	1시간 20분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293153_202606080442241251.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293153_202606080442241190.jpg	월요일(19:30)
5	PF293152	4	울산광역시 학생교육문화회관 기획공연, 세비야의 이발사 [울산]	2026-06-17	2026-06-17	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293152_260608_163341.jpg	서양음악(클래식)	공연예정	N	이승민 등	1시간 30분	전체 관람가	[공연소개] 로시니의 대표적인 희극 오페라들을 뮤지컬·오페라 콜라주 형식으로 재해석한 작품으로, 코미디 요소를 한층 강화한 ‘뮤직 코미디’ 공연입니다. 클래식 오페라 특유의 우아함에 가벼운 유머를 더해 부담 없이 웃으며 즐길 수 있는 무대를 선보입니다. 익숙한 멜로디와 경쾌한 리듬, 배우들의 활기찬 연기가 어우러져 오페라 초심자도 쉽게 몰입할 수 있으며, 오페라의 문턱을 낮춘 대중적인 공연으로 평가받고 있습니다. 특히 피가로 역에는 팬텀싱어, 언더커버 등을 통해 대중에게 잘 알려진 바리톤 이승민이 출연하여 탄탄한 가창력과 뛰어난 연기력을 선보입니다.	http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293152_202606080433419040.jpg	수요일(19:00)
6	PF293149	5	MyK FESTA (06.27)	2026-06-27	2026-06-27	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293149_260608_162340.jpg	대중음악	공연예정	N		2시간 30분	만 8세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293149_202606080423405480.jpg	토요일(19:00)
7	PF293148	5	MyK FESTA (06.26)	2026-06-26	2026-06-26	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293148_260608_162139.jpg	대중음악	공연예정	N		2시간 30분	만 8세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293148_202606080421398650.jpg	금요일(19:00)
8	PF293146	6	박정희 피아노 리사이틀 [부산]	2026-06-18	2026-06-18	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293146_260608_161503.jpg	서양음악(클래식)	공연예정	N	박정희	1시간 30분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293146_202606080415037931.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293146_202606080415037870.jpg	목요일(19:30)
9	PF293145	7	유령들 [서울]	2026-06-16	2026-06-21	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293145_260608_161503.png	연극	공연예정	N	우현주, 이석준, 한동규, 장석환, 문소희	1시간 30분	만 14세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293145_202606080415030510.png	화요일 ~ 금요일(19:30), 토요일 ~ 일요일(15:00)
10	PF293143	8	영도에서 떠나는 예술여행: 미술과 오페라의 만남 Ⅱ [부산]	2026-07-04	2026-07-04	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293143_260608_161442.jpg	서양음악(클래식)	공연예정	N	김성민, 윤경연, 조중혁, 신성희, 김란	1시간 30분	만 7세 이상	[프로그램] Giovanni Battista Pergolesi (1710~1736) Nina 니나 Tenor 조중혁 Piano 김란 Léo Delibes (1836~1891) Les filles de Cadix 카디스의 여인들 Soprano 윤경연 Piano 김란 Georges Bizet (1838~1875) L’amour est un oiseau rebelle 하바네라 Opera Carmen 오페라 카르멘 Mezzo soprano 신성희 Piano 김란 Georges Bizet (1838~1875) La fleur que tu m'avais jetée 당신이 나에게 던져준 꽃 Opera Carmen 오페라 카르멘 Tenor 조중혁 Piano 김란 매창 시 이원주 작곡 이화우 Soprano 윤경연 Piano 김란 이연주 작사 윤학준 작곡 잔향 Mezzo soprano 신성희 Piano 김란 Giacomo Puccini (1858~1924) Quando me'n vo' 내가 거리를 걸으면 Opera La Bohème 오페라 라보엠 Soprano 윤경연 Piano 김란 Giuseppe Verdi (1813~1901) Lunge da lei.. De' miei bollenti spiriti 그녀에게서 멀어지면.. 나의 끓어오르는 마음 Tenor 조중혁 Piano 김란 Francis Poulenc (1899~1963) Les chemins de l'amour 사랑의 길 Mezzo soprano 신성희 Piano 김란	http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293143_202606080414429530.jpg	토요일(11:00)
11	PF293142	9	모스크바홀 기획연주, 김학수 X 심재원: between notes, between bodies	2026-06-21	2026-06-21	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293142_260608_160829.png	복합	공연예정	N	김학수, 심재원	50분	전체 관람가	[공연소개] 소리는 움직임이 되고, 움직임은 다시 소리가 됩니다. 피아니스트 심재원과 댄서 Ghaksu는 작성된 악보도, 정해진 안무도 없이 무대에 오릅니다. 오직 서로의 존재와 공간, 그리고 순간에 대한 반응만이 공연을 이끕니다. 계획된 재현이 아닌, 지금 이곳에서만 존재하는 창작의 시간. 2026년 서초동 모스크바홀 기획공연 오디션 선정 아티스트들의 첫 무대를 선보입니다. 한 번의 순간, 한 번의 공연.	http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293142_202606080408294581.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293142_202606080408294390.jpg	일요일(17:00)
12	PF293141	10	한글먹고 얌얌 [수원]	2026-07-04	2026-07-04	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293141_260608_160828.gif	한국음악(국악)	공연예정	N	민현기, 김시은, 진기동, 현정석, 장보연, 장우찬, 김재민	1시간	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293141_202606080408289100.jpg	토요일(11:00,15:00)
13	PF293137	11	황치열 콘서트: 우리, 여름	2026-07-04	2026-07-04	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293137_260608_154850.gif	대중음악	공연예정	N	황치열	2시간	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293137_202606080348503570.jpg	토요일(14:00,18:00)
14	PF293135	12	깁스가족 [광주]	2026-06-12	2026-06-14	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293135_260608_154812.gif	연극	공연예정	N	박영진, 최이노, 이혜원, 정낙일, 송민종, 차성경	1시간 30분	만 6세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293135_202606080348130091.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293135_202606080348130000.jpg	금요일(20:00), 토요일(16:00,20:00), 일요일(16:00)
15	PF293134	13	싸이흠뻑쇼: SUMMERSWAG [대구]	2026-07-04	2026-07-05	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293134_260608_154413.gif	대중음악	공연예정	N	박재상		전체 관람가		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293134_202606080344139110.jpg	토요일 ~ 일요일(18:00)
16	PF293132	14	웨딩 브레이커 [고령]	2026-06-19	2026-06-19	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293132_260608_154131.jpg	연극	공연예정	N		1시간 30분	만 13세 이상	[공연소개] 2052년 미래, 당대 최고의 코미디언 임향한. 국민MC로 불리우는 그에게도 아픈 손가락이 있다. 그의 딸 17세 임이랑, 자신을 낳다 엄마가 죽자 아빠가 자길 미워한다 생각하는 금쪽이. 그녀는 ‘타임머신을 타고 과거로 돌아가 엄마와 아빠의 결혼을 막겠다!’ 결심하고 시간여행을 감행한다. 과거로 날아온 이랑은 엄마와 아빠가 처음 만난 개그 극단으로 숨어들기에 성공하는데...	http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293132_202606080341314330.jpg	금요일(19:00)
17	PF293124	15	화이트 노이즈 [대전]	2026-06-11	2026-06-13	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293124_260608_152545.gif	연극	공연예정	N	김은혁, 조경철, 이수아, 장은숙, 나윤주, 최승완, 최인수 등	1시간	전체 관람가		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293124_202606080325452862.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293124_202606080325452801.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293124_202606080325452740.jpg	목요일 ~ 금요일(19:30), 토요일(16:00)
18	PF293123	16	제4회 디아만테 앙상블 정기연주회: 어른들을 위한 동화 콘서트	2026-06-27	2026-06-27	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293123_260608_152343.gif	서양음악(클래식)	공연예정	N	임연진, 송나은, 김은서, 김재호, 유지혜	1시간 30분	만 8세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293123_202606080323436712.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293123_202606080323436431.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293123_202606080323436390.jpg	토요일(16:00)
19	PF293121	17	포항문화예술회관 소공연장 특별공연: 나우 스테이지 (NOW STAGE)	2026-06-19	2026-07-10	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293121_260608_151743.jpg	복합	공연예정	N	이현주, 신중용 등	1시간 20분	24개월 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293121_202606080317437640.jpg	금요일(19:30)
20	PF293117	18	김준수 1st 팬 콘서트: 준수한 판	2026-07-04	2026-07-04	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293117_260608_151259.jpg	한국음악(국악)	공연예정	N	김준수	1시간 40분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293117_202606080312598930.jpg	토요일(13:00,18:00)
21	PF293111	19	제34회 젊은연극제, 흥해도 청춘 망해도 청춘	2026-07-03	2026-07-04	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293111_260608_150344.png	연극	공연예정	N	김애리, 김수호, 구인영, 이수아, 백승덕, 정유정, 정국현 등	1시간 40분	만 16세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293111_202606080303440260.png	금요일(19:00), 토요일(15:00)
22	PF293107	20	손태진 X 린 콘서트: 여름밤의 세레나데 [경주]	2026-06-24	2026-06-24	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293107_260608_145650.jpg	대중음악	공연예정	N	손태진, 이세진	1시간 30분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293107_202606080256507511.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293107_202606080256507230.jpg	수요일(20:00)
23	PF293105	21	최소빈 발레단, 신데렐라 [용인]	2026-06-20	2026-06-20	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293105_260608_145135.gif	무용(서양/한국무용)	공연예정	N	박관우, 김서현, 고훈, 한가민, 김규리, 김규빈, 김래나 등	1시간 30분	48개월 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293105_202606080251357120.jpg	토요일(17:00)
24	PF293104	22	국립청년극단, 헤파이스토스 로미오와 줄리엣 [원주]	2026-06-26	2026-06-28	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293104_260608_145135.jpg	연극	공연예정	N	김빛나, 김윤서, 박상윤, 심효민, 윤방, 이서한, 이현우 등	1시간 30분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293104_202606080251352571.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293104_202606080251352090.jpg	금요일(19:30), 토요일(14:00,19:00), 일요일(14:00)
25	PF293102	23	블랙메리포핀스 리턴즈 데이	2026-06-30	2026-07-01	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293102_260608_144307.jpg	뮤지컬	공연예정	N	박정원, 문경초, 유태율, 윤승우, 원태민, 박준형, 김경록 등	1시간 40분	만 16세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293102_202606080245338530.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293102_202606080245338681.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293102_202606080245338742.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293102_202606080243077210.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293102_202606080247066940.jpg	화요일(20:00), 수요일(16:00,20:00)
26	PF293100	24	애니메이션 싱어롱 콘서트 [창원]	2026-06-14	2026-06-14	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293100_260608_143937.png	서양음악(클래식)	공연예정	N		1시간 10분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293100_202606080239379501.png|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293100_202606080239379330.png	일요일(17:00)
27	PF293099	25	BoA FAN CONCERT: BoA the MIC	2026-06-27	2026-06-28	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293099_260608_143937.jpeg	대중음악	공연예정	N	권보아	1시간 45분	만 6세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293099_202606080239372930.jpg	토요일(18:00), 일요일(16:00)
28	PF293098	1	이수민 & 신호철 듀오 리사이틀: 선율의 판타지 Ⅰ	2026-06-23	2026-06-23	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293098_260608_143447.png	서양음악(클래식)	공연예정	N	이수민, 신호철, 박경란, 방선혜	1시간 40분	만 4세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293098_202606080234479682.png|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293098_202606080234479471.png|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293098_202606080234479390.png	화요일(19:00)
29	PF293097	26	악기야놀자, 신나는 여름 (6월)	2026-06-20	2026-06-21	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293097_260608_143327.gif	서양음악(클래식)	공연예정	N		1시간 30분	24개월 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293097_202606080233273370.jpg	토요일(11:00), 일요일(13:00)
30	PF293093	27	쌀롱드무지끄, 돌섭듀오의 클래식 타임머신 첫 번째 이야기: 피터팬과 어린왕자	2026-06-20	2026-06-20	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293093_260608_142550.png	서양음악(클래식)	공연예정	N	이홍섭, 김한돌	1시간	만 5세 이상	[PROGRAM] * W. A. Mozart / Eine kleine Nachtmusik, K. 525  * C. Chaminade / Serenade d'automne * Hongsup Lee / - 옥인동 흰색 타일 집 - 무지개 - 소나기 * Handol Kim / - Spoon Scoop Waltz  - Variations on Cat's Dance  - Fur Elise Brillante  * M. Moszkowski / 4 Polish Folk Dances, Op.55, IV. Krakowiak  - 5 Valses, Op. 8 No. 3  - Deutsche Reigen, Op. 25 No. 3, 4  * J. Strauss / - Radetzky March  - Venetianer-Galopp, Op. 74	http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293093_202606080225500760.png	토요일(14:00)
31	PF293092	28	밀크레이프 해체주의	2026-06-17	2026-06-20	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293092_260608_142456.gif	연극	공연예정	N	박수영, 서채한, 김자령, 이주현	1시간	만 12세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293092_202606080224568040.png	수요일(19:30), 목요일(15:00,19:30), 금요일(19:30), 토요일(15:00,19:30)
32	PF293091	17	제125회 포항시립합창단 정기연주회: 6월의 위로	2026-06-18	2026-06-18	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293091_260608_142456.jpg	서양음악(클래식)	공연예정	N	최원익, 강유경, 전태현 등	1시간 20분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293091_202606080224562990.png	목요일(19:30)
33	PF293088	29	클라리넷페스트 오프닝 갈라 콘서트 [인천]	2026-07-07	2026-07-07	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293088_260608_141608.gif	서양음악(클래식)	공연예정	N	지중배, 이세연, 이도영, 비토르 페르난데스, 크리스텔 포셰, 채재일, 아넬린 반 바우베 등	1시간 40분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293088_202606080216083800.jpg	화요일(19:30)
34	PF293087	30	공명: The Resonance (길병민, 오스틴킴, 권서경)	2026-06-20	2026-06-20	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293087_260608_141607.gif	서양음악(클래식)	공연예정	N	서훈, 길병민, 권서경, 김태규 등	2시간	만 8세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293087_202606080216078250.jpg	토요일(19:00)
35	PF293085	31	고향의 봄 100주년 기념 한국가곡 듀오콘서트: 그리움	2026-06-14	2026-06-14	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293085_260608_140948.jpg	서양음악(클래식)	공연예정	N	송민태, 오금선 등	1시간 30분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293085_202606080216097680.jpg	일요일(17:00)
36	PF293084	32	싸이흠뻑쇼: SUMMERSWAG [의정부]	2026-06-27	2026-06-27	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293084_260608_140948.gif	대중음악	공연예정	N	박재상		전체 관람가		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293084_202606080209480150.jpg	토요일(18:00)
37	PF293080	33	국립심포니 콘서트 오케스트라: 영유아 음악회, 킨더 콘서트 [세종]	2026-06-18	2026-08-13	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293080_260608_140448.gif	서양음악(클래식)	공연예정	N		50분	전체 관람가		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293080_202606080204489490.jpg	목요일(11:00)
38	PF293078	34	알리오페라단, 세빌리아의 이발사 [영동]	2026-07-03	2026-07-04	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293078_260608_135511.jpg	서양음악(클래식)	공연예정	N	박희경, 박푸름, 조재경, 황승현, 박광우, 한지혜	1시간 20분	전체 관람가		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293078_202606080155114100.jpg	금요일(19:00), 토요일(14:00)
39	PF293076	35	울사운드 페스티벌	2026-06-13	2026-06-14	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293076_260608_135037.png	대중음악	공연예정	N		2시간	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293076_202606080150376560.png	토요일(18:00), 일요일(20:00)
40	PF293075	36	제71회 순천시립소년소녀합창단 정기연주회 [순천]	2026-06-13	2026-06-13	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293075_260608_135017.jpg	서양음악(클래식)	공연예정	N	권효진, 이후성, 이준성, 이미연 등	1시간 20분	만 4세 이상	[프로그램] 서막 [생명의 오딧세이] 소리의 탄생, 원초적 생명  - Adiemus  - 크레디션 1장 [평화의 오딧세이] 질서와 균형, 인간이 만든 평화와 공동체  - Dona nobis pacem  - Song of hope(타악기) 2장 [클래식 오딧세이] 미학적 공감, 보편적 언어  - 바이올린 솔로 3장 [안식의 오딧세이] 내면의 성찰, 휴식과 그리움  - 돌담에 속삭이는 햇발같이  - Der Lidenbaum  - Sanctus 4장 [순천 오딧세이] 뿌리와 장소의 기억 5장 [기쁨의 오딧세이] 에너지, 문화의 하나됨 *첼로 협연  - The Lion sleeps tonight  - Circle of Life  - 아리랑 연곡  - 경복궁 타령 에필로그 [귀환의 오딧세이]  - 흰 수염 고래	http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293075_202606080150173800.jpg	토요일(17:00)
41	PF293074	37	히든퍼즐 [대학로]	2026-07-01	2026-07-31	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293074_260608_135000.gif	연극	공연예정	N	남아진, 박정윤, 이나림, 최혜은, 권희대, 이슬마로, 정승진 등	1시간 20분	만 13세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293074_202606080150000170.jpg	월요일(14:30,17:00), 화요일 ~ 수요일(14:30), 금요일(14:30,17:00,19:30), 토요일(13:00,15:00,17:00,19:00), 일요일(13:00,15:00,17:00)
42	PF293072	38	수성못 뮤직앤비어 페스티벌 [대구]	2026-06-19	2026-06-21	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293072_260608_134535.png	대중음악	공연예정	N			만 19세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293072_202606080145359450.png	금요일(10:00), 토요일 ~ 일요일(14:00)
43	PF293071	39	어린이 마술콘서트, 쇼프라이즈 [서울 송파]	2026-06-27	2026-06-27	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293071_260608_134225.png	서커스/마술	공연예정	N		40분	30개월 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293071_202606080142253030.jpg	토요일(15:00,17:00)
44	PF293070	40	서초국제예술단 피아노 갈라 콘서트: 4Pianos 16Hands	2026-07-08	2026-07-08	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293070_260608_133857.jpg	서양음악(클래식)	공연예정	N	문명환, 김성훈, 금찬이, 황성순, 박선화, 심관섭, 김준희 등	1시간 40분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293070_202606080138579290.jpg	수요일(19:30)
45	PF293066	40	리움팸버오케스트라: 그랜드 콘체르토 콘서트 Ⅲ	2026-06-28	2026-06-28	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293066_260608_133440.png	서양음악(클래식)	공연예정	N	정홍식, 양고운, 이현지, 정지인, 송민제 등	1시간 40분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293066_202606080134408590.jpeg	일요일(19:30)
46	PF293062	41	딱지 [대구]	2026-06-26	2026-07-25	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293062_260608_132818.jpg	연극	공연예정	N	김재권, 박범진, 정선현, 박나연	1시간	만 13세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293062_202606080128186170.jpg	화요일 ~ 수요일(19:30), 금요일(19:30), 토요일(18:00)
47	PF293061	42	정도전 [영주]	2026-06-12	2026-06-13	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293061_260608_132817.jpg	뮤지컬	공연예정	N	손현진, 이우람, 백수민, 김창남, 김덕우, 안경애, 박성한 등	2시간	만 6세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293061_202606080128173850.jpg	금요일(19:00), 토요일(15:00,19:00)
48	PF293060	43	WHEN WE BLOOM 2: The songs we loved	2026-06-13	2026-06-13	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293060_260608_132514.jpg	서양음악(클래식)	공연예정	N	황혜진, 권기진 등	1시간	전체 관람가	[공연소개] The ACCORD Music X Holiday Cottage Ensemble BIS in Holiday Cottage 디 어코드뮤직과 홀리데이코티지가 전하는 네 번째 이야기 우리가 사랑했던 그 때, 그 시절 노래. 앙상블 비스의 스트링 연주로 그 때의 감성을 노래합니다.	http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293060_202606080125149122.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293060_202606080125149091.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293060_202606080125149030.png	토요일(17:00)
49	PF293058	44	국립민속국악원 소리 판 완창무대: 정주희의 김세종제 춘향가	2026-06-20	2026-06-20	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293058_260608_131953.jpg	한국음악(국악)	공연예정	N	정주희, 장보영, 서은기, 조용안	2시간	만 6세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293058_202606080119531330.jpg	토요일(14:00)
50	PF293057	45	Watering Gardeners plot.1 빅베트 (Bigbet)	2026-06-28	2026-06-28	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293057_260608_131741.jpg	대중음악	공연예정	N		2시간	전체 관람가		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293057_202606080117414980.jpg	일요일(17:00)
51	PF293056	46	YOON SAN-HA FANCON: JUST, NO REASON	2026-07-04	2026-07-05	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293056_260608_131316.jpg	대중음악	공연예정	N	윤산하	2시간	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293056_202606080113164840.jpg	토요일(18:00), 일요일(16:00)
52	PF293055	47	비브라토 방구석 클래식, 정승원의 ON AIR: SUMMER EDITION	2026-07-03	2026-07-03	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293055_260608_131249.jpg	서양음악(클래식)	공연예정	N	정승원	1시간	만 5세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293055_202606080112498931.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293055_202606080112498880.jpg	금요일(20:00)
53	PF293054	48	오늘을 기억해 [대구]	2026-06-13	2026-06-13	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293054_260608_131249.png	뮤지컬	공연예정	N	안상태, 정승환, 송영길, 김자미, 최지은, 김도후, 전소이	1시간 40분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293054_202606080112492650.png	토요일(15:00,19:00)
54	PF293053	49	Reciprocity: Round 4 SHOEGAZE MAZE	2026-06-27	2026-06-27	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293053_260608_130950.png	대중음악	공연예정	N	신윤수 등	2시간	만 14세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293053_202606080109502220.png	토요일(18:30)
55	PF293050	50	논산 스테이지 초이스 Ⅰ. 자이언티 X 비와이 [논산]	2026-06-26	2026-06-26	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293050_260608_130454.png	대중음악	공연예정	N		2시간	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293050_202606080104547730.png	금요일(19:00)
56	PF293049	51	NUIT ELECTRONIQUE	2026-06-19	2026-06-19	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293049_260608_130415.png	대중음악	공연예정	N	장 노엘 등	2시간	만 18세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293049_202606080104153230.png	금요일(20:00)
57	PF293048	52	허회경 단독 콘서트: Letter to Summer	2026-07-04	2026-07-05	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293048_260608_130147.gif	대중음악	공연예정	N	허회경	2시간	만 8세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293048_202606080101475110.jpg	토요일(18:00), 일요일(17:00)
58	PF293046	53	IDOL SUMMER JUNGLE 출연권쟁탈전 DAY3	2026-06-25	2026-06-25	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293046_260608_125803.png	대중음악	공연예정	N			전체 관람가		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293046_202606081258038501.png|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293046_202606081258038420.png	목요일(18:30)
59	PF293044	53	IDOL SUMMER JUNGLE 출연권쟁탈전 DAY2	2026-06-23	2026-06-23	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293044_260608_125408.jpg	대중음악	공연예정	N			전체 관람가		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293044_202606081254089151.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293044_202606081254089080.png	화요일(18:30)
60	PF293043	54	판타스틱 [광양]	2026-06-12	2026-06-12	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293043_260608_125331.jpg	뮤지컬	공연예정	N		1시간 20분	24개월 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293043_202606081255086520.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293043_202606081253312530.jpg	금요일(19:30)
61	PF293042	53	IDOL SUMMER JUNGLE 출연권쟁탈전 DAY1	2026-06-22	2026-06-22	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293042_260608_125330.jpg	대중음악	공연예정	N			전체 관람가		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293042_202606081253303831.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293042_202606081253303740.png	월요일(18:30)
62	PF293041	20	경주시립신라고취대 기획공연: 차세대 명인을 위한 협연의 밤 [경주]	2026-06-19	2026-06-19	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293041_260608_125135.png	한국음악(국악)	공연예정	N	김현호, 김소희, 이승빈, 서정원, 이종문, 정희윤, 김태환 등	1시간 40분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293041_202606081251358460.png	금요일(19:30)
63	PF293039	55	백석동 13블럭 [고양]	2026-06-23	2026-06-28	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293039_260608_124718.png	연극	공연예정	N	장두현, 최지숙, 이민재, 김주현, 홍석현, 왕승권, 심재근 등	1시간 20분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293039_202606081247187200.jpg	화요일 ~ 금요일(19:30), 토요일(18:00), 일요일(16:00)
64	PF293038	56	잭킹콩 여름 단독 공연: Summer For You [서울]	2026-07-04	2026-07-05	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293038_260608_124357.png	대중음악	공연예정	N	심강훈, 이범호, 고서원, 신유동, 장세훈	2시간	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293038_202606081243573570.png	토요일(18:00), 일요일(17:00)
65	PF293034	57	배진일의 춤, 황병기류 가야금 산조: 김명숙류 산조춤 소천素泉 전바탕	2026-06-17	2026-06-17	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293034_260608_123850.jpg	무용(서양/한국무용)	공연예정	N	배진일, 안나래, 김웅식	1시간 10분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293034_202606081238508920.jpg	수요일(19:30)
66	PF293033	58	IMAGINE the Stage, IMAGINE #02: 임정희	2026-06-19	2026-06-19	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293033_260608_123537.jpg	대중음악	공연예정	N	임정희, 박은비	1시간 30분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293033_202606081235372370.jpg	금요일(20:00)
67	PF293032	59	토끼와 자라 [광주]	2026-06-02	2026-06-30	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293032_260608_123315.jpg	뮤지컬	공연중	N		50분	전체 관람가	[공연소개] 안녕하세요~~ 아이들이 너무나 좋아하는 명작동화와 전래동화를 어린이들의 눈높이에 맞춰 공연하는 어린이들과 가족의 감성 놀이터이자 가족 뮤지컬 전문 공연장 [행복을주는가족극장]입니다. 따뜻한 봄이 지나고 초여름이 시작되는 6월! 아이들이 직접 함께 웃고 반응하며 즐길 수 있는 참여형 어린이 뮤지컬 [토끼와 자라]를 선보이니 많은 관심 부탁드립니다. 이번 공연은 익숙한 전래동화를 바탕으로 신나는 모험과 유쾌한 재미는 물론, 자연과 바다를 생각해보는 환경개선의 메시지까지 담아 더욱 뜻깊은 시간을 선물합니다. 어린 시절 좋은 공연 한 편은 아이들의 감성과 상상력, 그리고 밝은 마음을 키워주는 소중한 시간이 된답니다. 6월에 딱 어울리는 가족 공연, 부모와 자녀가 함께 웃고 공감할 수 있는 참여형 어린이 뮤지컬 [토끼와 자라]와 함께 아이들과 특별한 추억 만들어보시기를 적극 추천드립니다~~~^^*	http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293032_202606081233159572.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293032_202606081233159501.png|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293032_202606081233159450.jpg	화요일 ~ 금요일(10:20,11:20), 금요일 ~ 일요일(12:00,14:00,16:00)
68	PF293030	60	플레이티켓 낭독쇼케이스, 한성전화소 1905	2026-06-18	2026-06-19	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293030_260608_122728.jpg	연극	공연예정	N	박하늘, 김호은, 정혜원, 양하임, 김한별, 정윤영, 한결 등	1시간	만 13세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293030_202606081227283030.jpg	목요일 ~ 금요일(19:30)
69	PF293027	61	푸르지오아트홀 수요초대석 37, 한국피아노교수법학회 선정: Rising Pianists Concert	2026-06-10	2026-06-10	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293027_260608_121738.png	서양음악(클래식)	공연예정	N	이윤경, 이승원, 김진주, 권순아, 전소현, 이찬우, 이정화 등	1시간 40분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293027_202606081217389500.png	수요일(19:30)
70	PF293014	31	수성르네상스 프로젝트, 젊은 예술가 리사이틀 Ⅲ. 전보라 트롬본 리사이틀 [대구]	2026-06-24	2026-06-24	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293014_260608_113052.jpg	서양음악(클래식)	공연예정	N	전보라, 김효진	1시간 10분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293014_202606081130522481.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293014_202606081130522250.jpg	수요일(19:30)
71	PF293012	51	HYPER vol.3	2026-06-13	2026-06-13	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293012_260608_112646.png	대중음악	공연예정	N		6시간	만 18세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293012_202606081126469680.png	토요일(19:00)
72	PF293011	62	주인공 [서울]	2026-06-10	2026-06-14	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293011_260608_112646.gif	연극	공연예정	N	남윤성, 이재홍, 김미소, 김수연, 강민경, 손세빈, 김성영 등	1시간 30분	전체 관람가		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293011_202606081126464630.png	수요일 ~ 금요일(19:30), 토요일(15:00,19:30), 일요일(14:00)
73	PF293009	63	제14회 서울시 문화유산 판소리 수궁가 공개발표: 수궁가	2026-06-20	2026-06-20	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293009_260608_112231.jpg	한국음악(국악)	공연예정	N		2시간 46분	만 6세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293009_202606081122316760.jpg	토요일(15:00)
74	PF293008	64	유오 (UO) , Eternal Love in Seoul	2026-06-28	2026-06-28	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293008_260608_111656.png	대중음악	공연예정	N	권용현	1시간	전체 관람가		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293008_202606081116562650.jpg	일요일(17:00)
75	PF293007	65	빛의서막, 대한광복단 [전주]	2026-07-04	2026-07-04	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293007_260608_111435.gif	뮤지컬	공연예정	N	오세원, 나정원, 주희원, 류승완, 김지섭, 정찬혁, 김인휘 등	2시간	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293007_202606081114355300.jpg	토요일(15:00)
76	PF293002	66	제9회 아츠인탱크 무용축제 인코리아, 마라톤 공연	2026-07-03	2026-07-03	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293002_260608_110633.jpg	무용(서양/한국무용)	공연예정	N		1시간 40분	만 7세 이상	[공연소개] 서울 문화비축기지에서 개최되는 「제9회 아츠인탱크 무용축제 인 코리아(ADFK)」는 국내외 예술가와 시민이 함께 만드는 국제무용축제입니다. 미국·프랑스·호주·독일·영국·중국·일본 등 12개국 예술가들이 참여하며, 공연·워크숍·댄스필름·국제협업 프로젝트를 통해 동시대 무용의 흐름과 실험적 창작을 선보입니다. 6월 28일~7월 3일 동안 문화비축기지의 탱크 공간 전역에서 장르와 국적을 넘는 릴레이 공연, 국제 협업, 시민 참여 프로그램, 어린이·청소년 무용체험, 무용영화제 등이 펼쳐집니다. 특히 프랑스·미국 등 8개 해외 협력기관과의 연계를 통해 우수 작품의 해외 진출과 국제 교류를 지원하며, 공연–영상–해외연계로 이어지는 글로벌 무용 플랫폼 구조를 구축하고 있습니다. [프로그램] [마라톤공연] Vanessa Choi [홍콩] [마라톤공연] Aya Sakai [일본] [마라톤공연] ChavasseDance & Performance [미국] [국제협업 MDD 쇼케이스] 참여 아티스트 : 이영미, Kunhou, 성유림, 정승준, 신소정, Emmanuel Enoc Gonzalez, Ka Yan Tse, Maša Marković, Zhenhao Wen, 우태욱 [시민참여공연] <흥춤> 권명주 느루무용단 [시민참여공연/국제협업] <To You, I Surrender> Mark Gonzalez X 최보결	http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293002_202606081107319050.png	금요일(17:00)
77	PF293001	67	CHROMA KEY 005: MOVE AS ONE	2026-07-04	2026-07-04	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293001_260608_110218.jpg	대중음악	공연예정	N		6시간 10분	만 18세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293001_202606081102180840.jpg	토요일(18:00)
78	PF293000	68	baby selects, Westwood (웨스트우드) 서울 공연	2026-06-28	2026-06-28	http://www.kopis.or.kr/upload/pfmPoster/PF_PF293000_260608_105902.jpg	대중음악	공연예정	N		2시간	만 19세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293000_202606081059022502.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293000_202606081059022161.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF293000_202606081059021550.jpg	일요일(20:00)
79	PF292999	69	제28회 김천시립소년소녀합창단 정기연주회: 노래로 그리는 이땅의 숨결 [김천]	2026-06-19	2026-06-19	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292999_260608_105726.jpg	서양음악(클래식)	공연예정	N	이슬아, 김혜지 등	1시간	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292999_202606081057269080.jpg	금요일(19:30)
80	PF292996	70	대전아트필하모닉오케스트라 기획연주회2: 악마는 데시벨을 높인다	2026-07-01	2026-07-01	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292996_260608_105248.gif	서양음악(클래식)	공연예정	N	정치용, 최원휘 등	1시간 15분	만 7세 이상	[프로그램] · 오펜바흐 오페라 「천국과 지옥」 서곡 J. Offenbach _ Overture to the Opera 「Orpheus in the Underworld」   · 브라가 천사의 세레나데 G. Braga _ Angel’s Serenade   · 프랑크 생명의 양식 C. Franck _ Panis Angelicus -------------------- 테너 _ 최원휘   · 차이콥스키 모음곡 제4번, 작품 61 ‘모차르티아나’, 제3곡 기도 P. I. Tchaikovsky _ Suite No. 4, Op. 61 ‘Mozartiana’, Ⅲ. Preghiera - 휴 식 - · 슈베르트 마왕 (베를리오즈 관현악 편곡) F. Schubert _ The Erlking, D. 329 (Orch. H. Brelioz) -------------------- 테너 _ 최원휘   · 리스트 메피스토 왈츠 제1번, S.110 F. Liszt _ Mephisto Waltz No. 1 S. 110   · 생상스 죽음의 무도, 작품 40 C. Saint-Saëns _ Danse macaber, Op. 40   · 생상스 오페라 「삼손과 데릴라」 중 ‘바카날’ C. Saint-Saëns _ Samson et Dalila, Op. 47, ‘Bacchanal	http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292996_202606081052489860.jpg	수요일(19:30)
81	PF292995	31	수성아트피아 명품시리즈 Ⅴ, 빈 필하모닉 수석 하피스트 아넬레인 레나르츠 리사이틀 with 소프라노 황수미 [대구]	2026-07-03	2026-07-03	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292995_260608_105248.jpg	서양음악(클래식)	공연예정	N	아넬레인 레나르츠, 황수미	1시간 50분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292995_202606081052484710.jpg	금요일(19:30)
82	PF292993	71	ANTARES: JUNE	2026-06-13	2026-06-28	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292993_260608_104502.gif	대중음악	공연예정	N		1시간	전체 관람가		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292993_202606081045023300.gif	토요일 ~ 일요일(19:00)
83	PF292992	31	제9회 대구색소폰콰르텟 정기연주회 [대구]	2026-06-13	2026-06-13	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292992_260608_104501.jpg	서양음악(클래식)	공연예정	N	남경림, 유지현, 최기웅, 박세원, 최현	1시간	만 8세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292992_202606081045017571.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292992_202606081045017480.jpg	토요일(17:00)
84	PF292990	72	제30회 대구관악합주단 정기연주회 [대구]	2026-06-14	2026-06-14	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292990_260608_103749.png	서양음악(클래식)	공연예정	N	권승전, 김가현 등	1시간 30분	만 5세 이상	[프로그램]  Wind Orchestra Music from United Kingdom (영국의 윈드 오케스트라 음악)   · Pomp and Circumstances March No. 1 - Edward Elgar   위풍당당 행진곡 1번   · Fantasy on themes from Bizet’s <Carmen> for flute  - Francois Borne (Arranged by Marc Oliver)   플루트를 위한 <카르멘>주제의 환상곡    [협연] 김가현     Allegro moderato     · Tamna Fantasy - 박다은    탐라 환상곡 (2024 제주국제관악작곡콩쿠르 1위 없는 2위 및 특별상)   · Second Suite in F for Military Band - Gustav Holst   군악대를 위한 F장조 제2모음곡     I. March  II. Song without Words  III. Song of the Blacksmith  IV. Fantasia on the Dargason   - INTERMISSION -   · THE BANDWAGON - Philip Sparke   밴드웨건  · A Klezmer Karnival - Philip Sparke   클래즈머 카니발 · Suite from Hymn of the Highlands - Philip Sparke   하이랜드의 찬가 모음곡  I. Ardross Castle II. Alladale III. Dundonnell	http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292990_202606081037491310.png	일요일(17:00)
85	PF292988	73	78LIVE, 모스크바서핑클럽	2026-06-25	2026-06-25	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292988_260608_103256.gif	대중음악	공연예정	N		1시간 18분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292988_202606081032560740.jpg	목요일(19:30)
86	PF292987	74	믿고 보는 하늘	2026-06-25	2026-06-25	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292987_260608_103255.png	연극	공연예정	N	임규란, 이금정, 원서희	1시간	만 13세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292987_202606081032556184.png|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292987_202606081032556073.png|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292987_202606081032556022.png|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292987_202606081032555821.png|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292987_202606081032555110.png	목요일(20:00)
87	PF292984	75	제153회 강릉시립교향악단 정기연주회	2026-07-03	2026-07-04	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292984_260605_132421.png	서양음악(클래식)	공연예정	N	정민, 임동혁 등	2시간	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292984_202606050124212721.png|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292984_202606050124212580.png	금요일(19:30), 토요일(16:00)
88	PF292981	76	슬랩스틱: 스케르조 [평택]	2026-07-08	2026-07-08	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292981_260605_130615.jpg	뮤지컬	공연예정	N	빌렘 반 바센, 존 비트먼, 로지에 보스만, 산느 반 델프트	1시간 15분	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292981_202606050106157820.jpg	수요일(19:30)
89	PF292980	77	철조망: METAL SYNDICATE NETWORK, 저주파 12 CURSEWAVE+LOWFREQUENCY	2026-06-13	2026-06-13	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292980_260605_130120.jpg	대중음악	공연예정	N		3시간	전체 관람가	[공연소개] 저주파 12 CURSEWAVE+LOWFREQUENCY 低周波・詛呪波 XII 저주파 12 CURSEWAVE + LOWFREQUENCY DOOM, STONER AND SLUDGE NAHUA VARIM THE HOLY MOUNTAIN	http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292980_202606050101201360.jpg	토요일(18:30)
90	PF292977	78	대진대학교 연기예술학과, 모조인생	2026-06-11	2026-06-13	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292977_260605_114409.jpg	연극	공연예정	N	이승조, 시우현, 전소현, 정종환, 김민선, 이진, 최은서 등	2시간 20분	만 15세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292977_202606051144098880.png	목요일 ~ 금요일(19:30), 토요일(13:30,18:30)
91	PF292975	79	세컨드 액트 [춘천]	2026-07-04	2026-09-19	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292975_260605_113408.jpg	연극	공연예정	N	고은미, 서찬양, 고샛별, 성유승, 강대준, 주호	55분	만 12세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292975_202606051134082803.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292975_202606051134082652.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292975_202606051134082571.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292975_202606051134082390.jpg	토요일(14:00)
92	PF292974	80	제11회 서울페스티발앙상블 정기연주회	2026-06-23	2026-06-23	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292974_260605_112909.png	서양음악(클래식)	공연예정	N	최정연, 임경빈, 김문길, 박지현, 인태영, 나지영, 장세정 등	1시간 40분	만 6세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292974_202606051129094691.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292974_202606051129094610.jpg	화요일(19:30)
93	PF292970	75	1457, 소년 잠들다 [강릉]	2026-06-19	2026-06-19	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292970_260605_111542.jpg	뮤지컬	공연예정	N		1시간 30분	만 9세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292970_202606051115429002.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292970_202606051115428941.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292970_202606051115428880.jpg	금요일(19:30)
94	PF292967	81	코지 판 투테 [부산]	2026-06-19	2026-06-19	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292967_260605_110743.jpg	서양음악(클래식)	공연예정	N	조하정, 황신희, 이유현, 김민준, 이현준, 전의찬	1시간 30분	전체 관람가		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292967_202606051107433290.jpg	금요일(19:30)
95	PF292963	82	월간 피오레, 피아니스트 조은솔 (6월)	2026-06-24	2026-06-24	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292963_260605_105633.png	서양음악(클래식)	공연예정	N		1시간 30분	만 6세 이상	[공연소개] 연주자의 음악과 이야기가 함께 하는 클래식 토크쇼 월간 피오레 그 세번째 주인공 '조은솔 피아니스트' 이번 주제는 '내가 음악을 사랑하게 된 이유' 입니다. 어릴적 한국에서 음악 교육을 받다 유학을 결심하고 어린 나이에 미국으로 넘어가 미국에서의 음악교육을 받으며  자신만의 음악을 구축해 나간 조은솔 피아니스트의 진심어린 이야기를 그녀가 애정하는 음악들과 함께 들어보시길 바랍니다. [PROGRAM] J. S. Bach - Italian Concerto in F Major, BWV 971 C. Debussy - Suite Bergamasque J. Brahms - Intermezzo Op. 118 No. 2 E. Granados - Valses poeticos N. Kapustin - Variations Op. 41	http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292963_202606051056338190.png	수요일(19:00)
96	PF292962	83	CELL [인천]	2026-06-20	2026-06-21	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292962_260605_105632.jpg	무용(서양/한국무용)	공연예정	N	김승환, 손수정, 한아름, 박재이, 김기태	1시간	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292962_202606051056329750.jpg	토요일 ~ 일요일(16:00)
97	PF292961	84	수상한스테이지 (06.12)	2026-06-12	2026-06-12	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292961_260605_105348.png	대중음악	공연예정	N	도이주 등	2시간	만 15세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292961_202606051053488440.png|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292961_202606051057559440.png|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292961_202606051057559531.png|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292961_202606051057559642.png	금요일(20:00)
98	PF292958	85	겁쟁이 빌리 [부천]	2026-07-04	2026-07-26	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292958_260605_104400.jpg	뮤지컬	공연예정	N		50분	전체 관람가		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292958_202606051044007181.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292958_202606051044007150.jpg	토요일 ~ 일요일(12:00,14:00)
99	PF292956	86	드레스덴 슈타츠카펠레 체임버 오케스트라 [제주 서귀포]	2026-07-01	2026-07-01	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292956_260605_104055.jpg	서양음악(클래식)	공연예정	N		2시간	만 7세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292956_202606051042550480.jpg|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292956_202606051042550531.png|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292956_202606051042550653.png|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292956_202606051042550602.png|http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292956_202606051042550714.png	수요일(19:30)
100	PF292955	87	펜과 검	2026-07-02	2026-07-12	http://www.kopis.or.kr/upload/pfmPoster/PF_PF292955_260605_103841.png	연극	공연예정	N	경지은, 김주빈, 박진호, 송석근, 이진경	1시간 40분	만 13세 이상		http://www.kopis.or.kr/upload/pfmIntroImage/PF_PF292955_202606051038414450.png	월요일(19:30), 수요일 ~ 금요일(19:30), 토요일 ~ 일요일(15:00)
\.


--
-- TOC entry 4919 (class 0 OID 16420)
-- Dependencies: 220
-- Data for Name: venues; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.venues (id, kopis_id, name, address, province, district, seat_capacity, phone, latitude, longitude, halls_text) FROM stdin;
1	FC000567	꿈의숲아트센터	서울특별시 강북구 월계로 173 (번동)	서울	강북구	584	02-2289-5401	37.62143120000000	127.04062460000000	퍼포먼스홀:283|콘서트홀:301|야외 볼프라자:0|상상톡톡 미술관:0
2	FC000001	예술의전당 [서울]	서울특별시 서초구 남부순환로 2406 (서초동)	서울	서초구	164344	02-580-1300	37.47868960000000	127.01182410000001	CJ 토월극장:1,004|리사이틀홀:354|콘서트홀:2,505|자유소극장:241|IBK챔버홀:600|오페라극장:2,283|신세계스퀘어 야외무대:1,000|인춘아트홀:100|1101어린이라운지:0|서예박물관:0|N스튜디오(국립예술단체공연연습장) 공용1:20
3	FC000384	영산아트홀	서울특별시 영등포구 여의공원로 101 (여의도동)	서울	영등포구	598	02-6181-5260	37.52923090000000	126.92487210000002	영산아트홀:598
4	FC003382	울산광역시학생교육문화회관	울산광역시 중구 곽남길 95(약사동)	울산	중구	706	052-290-5600	35.57360480000000	129.33827160000000	대공연장(소원홀):706
5	FC001910	킨텍스	경기도 고양시 일산서구 킨텍스로 217-60 (대화동)	경기	고양시	2800	031-995-8036	37.66930710000000	126.74568449999992	야외공연장:800|제2전시장:1,000|제1전시장:1,000|제2전시장 9홀:0|제2전시장 7,8홀:0|제2전시장 10홀:0|제1전시장 1홀:0|제1전시장 2홀:0|제1전시장 3홀:0|제1전시장 5홀:0|제2전시장 6홀:0
6	FC000160	금정문화회관	부산광역시 금정구 체육공원로 7 (구서동)	부산	금정구	1574	051-519-5651	35.24590850000000	129.09413780000000	대공연장(금빛누리홀):880|소공연장(은빛샘홀):394|야외공연장:300
7	FC000526	연우소극장	서울특별시 종로구 창경궁로35길 21 (혜화동)	서울	종로구	100	02-744-7090	37.58695150000000	127.00175280000008	연우소극장:100
8	FC000828	영도문화예술회관	부산광역시 영도구 함지로79번길 6 (동삼동)	부산	영도구	1188	051-419-5571	35.07533520000000	129.06601109999997	대공연장(봉래홀):428|소공연장(절영홀):160|학여울마당:600
9	FC004317	모스크바홀	서울특별시 서초구 효령로 242 (서초동)	서울	서초구	50		37.48367060000000	127.01059190000000	모스크바홀:50
10	FC003664	정조테마공연장	경기도 수원시 팔달구 정조로 817 (팔달로1가)	경기	수원시	258	031-290-3578	37.28102120000000	127.01621580000000	정조테마공연장:258
11	FC002122	노들섬	서울특별시 용산구 양녕로 445 (이촌동)	서울	용산구	1072	02-6365-1008	37.51704640000000	126.96021960000000	잔디마당:616|라이브하우스:456|뮤직라운지: 류:0|다목적 홀: 숲:0|3층 테라스:0
12	FC001305	씨어터연바람	광주광역시 동구 구성로204번길 1-1(대인동)	광주	동구	60	062-226-2446	35.14915610000000	126.92363730000000	씨어터연바람:60
13	FC001965	대구스타디움	대구광역시 수성구 유니버시아드로 180 (대흥동)	대구	수성구	68922	053-803-8323	35.82993770000000	128.69015630000000	주경기장:66,422|보조경기장:2,500|서편 광장:0|동편 광장:0
14	FC000863	경북고령대가야문화누리 (구. 대가야국악당)	경상북도 고령군 대가야읍 왕릉로 30	경북	고령군	778	054-950-7014	35.72658480000000	128.26361260000000	대공연장 (우륵홀):638|소공연장 (가야금홀):140|야외공연장:0
15	FC001194	대전 서구 관저문예회관	대전광역시 서구 관저동로105번길 20	대전	서구	254	042-288-2790	36.30168159999999	127.33943230000000	대전 서구 관저문예회관:254
16	FC003195	거암아트홀	서울특별시 강남구 강남대로 652(신사동)	서울	강남구	144		37.51951010000000	127.01910600000000	거암아트홀:144
17	FC001191	포항문화예술회관	경상북도 포항시 남구 희망대로 850 (대도동)	경북	포항시	1527	054-289-7999	36.00954800000000	129.36599270000000	대공연장:963|소공연장:264|야외공연장:300
18	FC001799	이화여자대학교 삼성홀	서울특별시 서대문구 이화여대길 52 (대현동)	서울	서대문구	702	02-6380-4430	37.56142380000000	126.94697270000006	이화여자대학교 삼성홀:702
19	FC001250	보라 아트홀(구. 지구인아트홀)	서울특별시 종로구 창경궁로 260 (명륜2가)	서울	종로구	170	02-745-3641	37.58438480000000	127.00051899999994	보라 아트홀(구. 지구인아트홀):170
20	FC000517	경주예술의전당	경상북도 경주시 알천북로 1 (황성동)	경북	경주시	3184	054-777-2949	35.86258690000000	129.20586520000006	대공연장(화랑홀):1,053|소공연장(원화홀):331|야외공연장:900|로비(2층):0|대회의실:0|대연습실:0
21	FC000823	용인시문화예술회관	경기도 용인시 처인구 중부대로1392번길 15 (김량장동)	경기	용인시	626	031-260-3300	37.23171330000000	127.19885390000002	처인홀:626
22	FC004714	태장공연장	강원특별자치도 원주시 치악로 2068-6 (태장동)	강원	원주시	204		37.36407000000000	127.96412400000000	공연장:204
23	FC003244	링크아트센터	서울특별시 종로구 대학로14길 29(혜화동)	서울	종로구	860		37.58468990000000	127.00229470000000	페이코홀:470|벅스홀:390
24	FC000244	진해문화센터 (진해구민회관)	경상남도 창원시 진해구 진해대로 325 (태백동) 진해구민센터	경남	창원시	1359	055-719-7882	35.16911870000000	128.65962420000005	공연장:395|야외공연장:964
25	FC001792	연세대학교 대강당	서울특별시 서대문구 연세로 50 (신촌동)	서울	서대문구	1641	02-2123-3818	37.56431220000000	126.93891789999998	연세대학교 대강당:1,641
26	FC000014	충무아트센터	서울특별시 중구 퇴계로 387 (흥인동)	서울	중구	2045	02-2230-6601	37.56601390000000	127.01481309999997	소극장 블루:225|대극장:1,250|중극장 블랙:320|컨벤션센터:150|예그린스페이스:100
27	FC002062	쌀롱드무지끄	서울특별시 종로구 창의문로 129 (부암동)	서울	종로구	20	010-8826-8364	37.59236440000000	126.96599500000000	쌀롱드무지끄:20
28	FC004260	이화여자대학교 생활환경관 소극장	서울특별시 서대문구 이화여대길 52 (대현동)	서울	서대문구	200	02-3277-2114	37.56446450000000	126.95028880000000	이화여자대학교 생활환경관 소극장:200
29	FC001873	아트센터 인천	인천광역시 연수구 아트센터대로 222 (송도동)	인천	연수구	3796	032-453-7700	37.39348409999999	126.63095859999999	콘서트홀:1,727|다목적홀:342
30	FC001486	고려대학교 인촌기념관	서울특별시 성북구 안암로 145 (안암동5가)	서울	성북구	980	02-3290-1114	37.58866810000000	127.03513470000007	대강당:980
31	FC000204	수성아트피아	대구광역시 수성구 무학로 180 (지산동)	대구	수성구	1460	053-666-3300	35.82954260000000	128.62841500000002	대극장 (대공연장):1,159|소극장 (소공연장):301|대극장 로비:0
32	FC002627	의정부 종합운동장	경기도 의정부시 체육로 90 (녹양동)	경기	의정부시	28000	031-828-6882	37.75793500000000	127.03160680000000	종합운동장:28,000
33	FC002877	세종예술의전당	세종특별자치시 국립박물관로 21(나성동)	세종	세종특별자치시	1071	044-850-8921	36.48667080000000	127.26736770000000	대공연장:1,071|중공연장:0|소공연장:0|야외공연장:0|다목적실 (3F):0|로비:0
34	FC002922	영동복합문화예술회관	충청북도 영동군 영동읍 영동힐링로 117	충북	영동군	416		36.15635340000000	127.78651370000000	영동복합문화예술회관:416
35	FC001328	울산중구문화의전당	울산광역시 중구 종가로 405 (성안동)	울산	중구	1022	052-290-4000	35.56754220000000	129.32153640000000	함월홀 (2층):499|달빛마루 (2층):200|별빛마루 (1층):200|어울마루 (지하):123|야외 잔디마당:0
36	FC000493	순천문화예술회관	전라남도 순천시 삼산로 16 (석현동)	전남	순천시	1066	061-749-8612	34.97058410000000	127.48531440000000	대극장:914|소극장:152
37	FC001207	컬쳐씨어터(구. 휴먼시어터)	서울특별시 종로구 대학로8가길 80 (동숭동)	서울	종로구	120	010-9012-6001	37.58245180000000	127.00325190000001	컬쳐씨어터(구. 휴먼시어터):120
38	FC004915	수성못 상화동산	대구광역시 수성구 무학로 112 (두산동)	대구	수성구	0		35.82918500000000	128.62059100000000	수성못 상화동산:0
39	FC003364	송파어린이문화회관	서울특별시 송파구 중대로 235(오금동)	서울	송파구	154	02-449-0505	37.50274250000000	127.12840040000000	아이소리홀:154
40	FC001513	롯데콘서트홀	서울특별시 송파구 올림픽로 300 (신천동) 롯데월드몰 8층 롯데문화재단	서울	송파구	2036	00-1544-7744	37.51306050000000	127.10349500000007	롯데콘서트홀:2,036
41	FC001552	동아백화점 아트홀	대구광역시 중구 달구벌대로 2085 (덕산동)	대구	중구	124	053-251-3371	35.86631370000000	128.59184740000000	동아백화점 아트홀:124
42	FC000050	영주문화예술회관	경상북도 영주시 가흥로 257 (가흥동)	경북	영주시	498	054-639-5951	36.81840050000000	128.60536649999995	까치홀:498
43	FC004350	홀리데이 코티지 (Holiday Cottage)	충청북도 청주시 청원구 내수읍 세교초정로 47	충북	청주시	0		36.70680100000000	127.57143450000000	홀리데이 코티지 (Holiday Cottage):0
44	FC001316	국립민속국악원	전라북도 남원시 양림길 54 - 0 국립민속국악원	전북	남원시	744	063-620-2324	35.40182620000000	127.39142549999997	예원당:644|예음헌:100
45	FC002028	생기 스튜디오	서울특별시 마포구 와우산로 137 (서교동)	서울	마포구	70	010-5354-0193	37.55386440000000	126.92858460000000	생기 스튜디오:70
46	FC000156	티켓링크 1975 씨어터(구.능동 어린이회관)	서울특별시 광진구 광나루로 441 (능동)	서울	광진구	1110	02-2204-6028	37.54650040000000	127.07880590000002	티켓링크 1975 씨어터(구.무지개극장):1,010|이벤트홀:100|유니아트센터:0
47	FC004848	비브라토 플러스	서울특별시 마포구 토정로3길 9 (합정동)	서울	마포구	20		37.54603500000000	126.91406600000000	비브라토 플러스:20
48	FC000836	대구서구문화회관	대구광역시 서구 당산로 403 (이현동)	대구	서구	822	053-663-3081	35.87227320000000	128.54557730000000	공연장:452|야외공연장:370
49	FC004608	듈스튜디오	서울특별시 마포구 잔다리로 20 (서교동)	서울	마포구	0		37.55094400000000	126.92083200000000	듈스튜디오:0
50	FC001182	논산아트센터(구. 논산문화예술회관)	충청남도 논산시 시민로 270 (내동)	충남	논산시	729	041-746-5950	36.19091780000000	127.09514979999994	대공연장:560|소공연장:169
51	FC004831	심심(XIMXIM)	서울특별시 성동구 연무장15길 11 (성수동2가)	서울	성동구	0		37.54262300000000	127.05928300000000	심심(XIMXIM):0
52	FC001216	서강대 메리홀	서울특별시 마포구 백범로 35 서강대학교	서울	마포구	528	02-705-8743	37.54995280000000	126.93911270000001	대극장:428|소극장:100
53	FC004646	아스트라홀	서울특별시 마포구 동교로22길 14 (서교동)	서울	마포구	150		37.55511400000000	126.91881600000000	아스트라홀:150
54	FC000743	광양시문화예술회관	전라남도 광양시 광양읍 향교길 9-30	전남	광양시	679	061-797-2529	34.97998270000000	127.58758920000002	대공연장:490|소공연장:189
55	FC003668	13블럭 소극장	경기도 고양시 일산동구 강촌로26번길 7-21 (백석동)	경기	고양시	60	010-7720-8607	37.64708880000000	126.78011020000000	공연장:60
56	FC000082	CJ아지트 광흥창	서울특별시 마포구 창전로 14 (신정동) CJ아지트	서울	마포구	250	02-3272-2616	37.54423110000000	126.93044699999996	CJ아지트 광흥창:250
57	FC000009	국립국악원	서울특별시 서초구 남부순환로 2364 (서초동) 국립국악원	서울	서초구	2449	02-580-3300	37.47860940000000	127.01130690000002	예악당:658|우면당:231|풍류사랑방:130|연희마당:700|진악당(폐관):600
58	FC003917	홍대 카페 (구.홍대카페)	서울특별시 마포구 어울마당로 68 (서교동)	서울	마포구	650	010-8877-5497	37.55109730000000	126.92149390000000	ROOF TOP (9F):500|STAGE (B1):150|LP MUSIC(6F):0|갤러리 (5F):0
59	FC003589	롯데마트 [월드컵]	광주광역시 서구 금화로 240 (풍암동)	광주	서구	50		35.13364610000000	126.87482990000000	행복을 주는 가족극장:50
60	FC004787	서울문화예술교육센터 강북	서울특별시 강북구 솔샘로48길 14 (미아동)	서울	강북구	10	02-2105-2319	37.61955000000000	127.01760700000000	예술당솔샘(2F):10
61	FC002246	푸르지오아트홀	서울특별시 중구 을지로 170 (을지로4가)	서울	중구	280	02-2288-2864	37.56617920000000	126.99732420000000	푸르지오아트홀:280
62	FC001636	다케이씨어터 (구. 창조소극장)	서울특별시 종로구 창경궁로 259 (명륜2가)	서울	종로구	110		37.58451489999999	127.00002580000000	다케이씨어터 (구. 창조소극장):110
63	FC001441	서울돈화문국악당	서울특별시 종로구 율곡로 102 - 0	서울	종로구	138	02-3210-7001	37.57720090000000	126.99067390000005	서울돈화문국악당:138|국악마당:0
64	FC003185	연남스페이스	서울특별시 마포구 성미산로22길 16(연남동)	서울	마포구	280		37.56215810000000	126.92088180000000	연남스페이스:280
65	FC000477	한국소리문화의전당	전라북도 전주시 덕진구 소리로 31 (덕진동1가) 소리문화전당	전북	전주시	10359	063-270-8000	35.85524500000000	127.13766699999996	야외공연장:7,000|모악당:2,037|명인홀:206|연지홀:666|국제회의장:250|중정:100|전시장 옥상:100|전시장 (2F):0
66	FC002153	문화비축기지	서울특별시 마포구 증산로 87 (성산동)	서울	마포구	11180	02-376-8410	37.57160730000000	126.89536900000000	문화마당:10,000|T1 1번 탱크 파빌리온:200|2번 탱크 실내공연장:300|T2 야외무대:400|4번 탱크:250|원형회의실:30
67	FC001841	파라다이스시티	인천광역시 중구 영종해안남로321번길 186 (운서동)	인천	중구	1820	00-1833-8855	37.43354510000000	126.45920019999994	그랜드볼륨:1,820|컬처파크 (야외):0|클럽 크로마:0|스튜디오 파라다이스:0
68	FC002813	스페이스브릭 (SPACE BRICK)	서울특별시 마포구 잔다리로 31(서교동)	서울	마포구	60		37.55120200000000	126.91968870000000	스페이스브릭 (SPACE BRICK):60
69	FC003446	김천시립율곡도서관	경상북도 김천시 용전1로1길 17 (율곡동)	경북	김천시	464	054-421-0200	36.12216590000000	128.18880680000000	율곡홀 (다목적강당):464
70	FC000076	대전예술의전당	대전광역시 서구 둔산대로 135 (만년동)	대전	서구	3039	042-270-8333	36.36652110000000	127.38371350000000	아트홀:1,546|앙상블홀:643|원형극장:850|연습실 (1F):0
71	FC001624	K-POP STAGE (구. 윤형빈소극장 [홍대] )	서울특별시 마포구 와우산로21길 29 (서교동)	서울	마포구	147		37.55218660000000	126.92236730000000	K-POP STAGE (구. 윤형빈소극장 [홍대] ):147
72	FC001193	대구콘서트하우스	대구광역시 중구 태평로 141 (태평로2가)	대구	중구	2192	053-250-1400	35.87604710000000	128.59384449999993	그랜드홀 (대공연장):1,284|챔버홀 (소공연장):248|로비 및 야외:660
73	FC002622	엠피엠지	서울특별시 마포구 서강로 78 (창전동)	서울	마포구	30	02-322-5684	37.55005590000000	126.93259970000000	LOUNGE M.:30
74	FC002589	성수 소극장(일루미 스튜디오)	서울특별시 성동구 성덕정길 135-1 (성수동2가)	서울	성동구	90	02-6396-5785	37.53667330000000	127.05840540000000	성수 소극장(일루미 스튜디오):90
75	FC001787	강릉아트센터 (구. 강릉문화예술관)	강원도 강릉시 종합운동장길 84 (교동)	강원	강릉시	1637	033-660-6800	37.77168460000000	128.89530500000000	사임당홀 (대공연장):972|소공연장:385|야외공연장:150|북카페:100|제3전시실:0|제1전시실:0|예술교육실:30
76	FC000934	평택시남부문예회관	경기도 평택시 중앙로 277 (비전동)	경기	평택시	862	031-8024-5411	36.99092190000000	127.11427630000003	대공연장:606|소공연장:256
77	FC004911	딥퍼플	서울특별시 서대문구 연세로7안길 34-6 (창천동)	서울	서대문구	0		37.55834700000000	126.93506300000000	딥퍼플:0
78	FC001950	대진대학교	경기도 포천시 호국로 1007 (선단동)	경기	포천시	6304	031-539-1114	37.87343460000000	127.15739860000000	실내체육관:6,254|예술관 소극장:50|예술관 스튜디오극장:0
79	FC002254	소극장 연극바보들	강원도 춘천시 서부대성로239번길 7 (효자동)	강원	춘천시	74	010-4610-8343	37.87334670000000	127.74483610000000	소극장 연극바보들:74
80	FC000020	세종문화회관	서울특별시 종로구 세종대로 175 (세종로)	서울	종로구	5372	02-399-1000	37.57252540000000	126.97564290000003	세종대극장:3,022|세종체임버홀:443|세종M씨어터:609|세종S씨어터:330|뜨락 (야외공간) (폐관):0|세종예술아카데미 (스퀘어홀):94|세종예술아카데미 (서클홀):50|세종예술아카데미 (오픈스테이지):100
81	FC000827	부산북구문화예술회관 (구.북구문화빙상센터)	부산광역시 북구 금곡대로46번길 50 (덕천동)	부산	북구	341	051-309-4087	35.21344910000000	129.00546810000003	공연장:341
82	FC004802	피오레아트앤엔터(피오레움)	서울특별시 서초구 효령로52길 16 (서초동)	서울	서초구	0		37.48359900000000	127.01284400000000	공연장:0
83	FC001310	인천아트플랫폼	인천광역시 중구 제물량로218번길 3 - 0 인천아트플랫폼	인천	중구	30	032-760-1000	37.47292950000000	126.62004730000001	공연장 (C동):30
84	FC003365	수상한창고	서울특별시 금천구 금하로24길 7(시흥동)	서울	금천구	35	070-8812-2020	37.45065810000000	126.90881590000000	수상한창고:35
85	FC002478	뉴코아소극장 [부천]	경기도 부천시 송내대로 239 (상동)	경기	부천시	160	032-624-8120	37.50411990000000	126.75663150000000	뉴코아소극장 [부천]:160
86	FC001231	서귀포예술의전당	제주특별자치도 서귀포시 태평로 270 (서홍동)	제주	서귀포시	1115	064-760-3341	33.24523060000000	126.55175259999999	대극장:802|소극장:190|야외공연장:123
87	FC001529	여행자극장	서울특별시 성북구 성북로5길 9-3 (성북동1가)	서울	성북구	100	070-7918-9077	37.58890860000000	127.00463660000003	여행자극장:100
\.


--
-- TOC entry 4929 (class 0 OID 0)
-- Dependencies: 221
-- Name: performances_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.performances_id_seq', 1, false);


--
-- TOC entry 4930 (class 0 OID 0)
-- Dependencies: 219
-- Name: venues_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.venues_id_seq', 1, false);


--
-- TOC entry 4767 (class 2606 OID 16442)
-- Name: performances performances_kopis_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.performances
    ADD CONSTRAINT performances_kopis_id_key UNIQUE (kopis_id);


--
-- TOC entry 4769 (class 2606 OID 16440)
-- Name: performances performances_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.performances
    ADD CONSTRAINT performances_pkey PRIMARY KEY (id);


--
-- TOC entry 4763 (class 2606 OID 16430)
-- Name: venues venues_kopis_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.venues
    ADD CONSTRAINT venues_kopis_id_key UNIQUE (kopis_id);


--
-- TOC entry 4765 (class 2606 OID 16428)
-- Name: venues venues_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.venues
    ADD CONSTRAINT venues_pkey PRIMARY KEY (id);


--
-- TOC entry 4770 (class 2606 OID 16443)
-- Name: performances performances_venue_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.performances
    ADD CONSTRAINT performances_venue_id_fkey FOREIGN KEY (venue_id) REFERENCES public.venues(id);


-- Completed on 2026-06-09 18:50:44

--
-- PostgreSQL database dump complete
--

\unrestrict O3ZcvpiGXy25D6gDTu2RbHXBBNwmSXdhWMIAN9JhARKaH2iTjR5gZohjQ0bspXl

