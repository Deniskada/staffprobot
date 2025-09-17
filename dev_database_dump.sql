--
-- PostgreSQL database dump
--

-- Dumped from database version 15.4 (Debian 15.4-1.pgdg110+1)
-- Dumped by pg_dump version 15.4 (Debian 15.4-1.pgdg110+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

DROP DATABASE IF EXISTS staffprobot_dev;
--
-- Name: staffprobot_dev; Type: DATABASE; Schema: -; Owner: postgres
--

CREATE DATABASE staffprobot_dev WITH TEMPLATE = template0 ENCODING = 'UTF8' LOCALE_PROVIDER = libc LOCALE = 'C';


ALTER DATABASE staffprobot_dev OWNER TO postgres;

\connect staffprobot_dev

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: staffprobot_dev; Type: DATABASE PROPERTIES; Schema: -; Owner: postgres
--

ALTER DATABASE staffprobot_dev SET search_path TO '$user', 'public', 'topology', 'tiger';


\connect staffprobot_dev

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: tiger; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA tiger;


ALTER SCHEMA tiger OWNER TO postgres;

--
-- Name: tiger_data; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA tiger_data;


ALTER SCHEMA tiger_data OWNER TO postgres;

--
-- Name: topology; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA topology;


ALTER SCHEMA topology OWNER TO postgres;

--
-- Name: SCHEMA topology; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA topology IS 'PostGIS Topology schema';


--
-- Name: fuzzystrmatch; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS fuzzystrmatch WITH SCHEMA public;


--
-- Name: EXTENSION fuzzystrmatch; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION fuzzystrmatch IS 'determine similarities and distance between strings';


--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


--
-- Name: postgis_tiger_geocoder; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder WITH SCHEMA tiger;


--
-- Name: EXTENSION postgis_tiger_geocoder; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis_tiger_geocoder IS 'PostGIS tiger geocoder and reverse geocoder';


--
-- Name: postgis_topology; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis_topology WITH SCHEMA topology;


--
-- Name: EXTENSION postgis_topology; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis_topology IS 'PostGIS topology spatial types and functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: contract_templates; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.contract_templates (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    content text NOT NULL,
    version character varying(50) NOT NULL,
    is_active boolean NOT NULL,
    created_by integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone,
    is_public boolean NOT NULL,
    fields_schema json
);


ALTER TABLE public.contract_templates OWNER TO postgres;

--
-- Name: contract_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.contract_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.contract_templates_id_seq OWNER TO postgres;

--
-- Name: contract_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.contract_templates_id_seq OWNED BY public.contract_templates.id;


--
-- Name: contract_versions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.contract_versions (
    id integer NOT NULL,
    contract_id integer NOT NULL,
    version_number character varying(50) NOT NULL,
    content text NOT NULL,
    changes_description text,
    created_by integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.contract_versions OWNER TO postgres;

--
-- Name: contract_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.contract_versions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.contract_versions_id_seq OWNER TO postgres;

--
-- Name: contract_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.contract_versions_id_seq OWNED BY public.contract_versions.id;


--
-- Name: contracts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.contracts (
    id integer NOT NULL,
    contract_number character varying(100) NOT NULL,
    owner_id integer NOT NULL,
    employee_id integer NOT NULL,
    template_id integer,
    title character varying(255) NOT NULL,
    content text,
    hourly_rate integer,
    start_date timestamp with time zone NOT NULL,
    end_date timestamp with time zone,
    status character varying(50) NOT NULL,
    is_active boolean NOT NULL,
    allowed_objects json,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone,
    signed_at timestamp with time zone,
    terminated_at timestamp with time zone,
    "values" json
);


ALTER TABLE public.contracts OWNER TO postgres;

--
-- Name: contracts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.contracts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.contracts_id_seq OWNER TO postgres;

--
-- Name: contracts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.contracts_id_seq OWNED BY public.contracts.id;


--
-- Name: objects; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.objects (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    owner_id integer NOT NULL,
    address text,
    coordinates character varying(100) NOT NULL,
    opening_time time without time zone NOT NULL,
    closing_time time without time zone NOT NULL,
    hourly_rate numeric(10,2) NOT NULL,
    required_employees text,
    is_active boolean,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    max_distance_meters integer DEFAULT 500 NOT NULL,
    auto_close_minutes integer DEFAULT 60 NOT NULL,
    available_for_applicants boolean,
    work_days_mask integer DEFAULT 31 NOT NULL,
    schedule_repeat_weeks integer DEFAULT 1 NOT NULL,
    timezone character varying(50)
);


ALTER TABLE public.objects OWNER TO postgres;

--
-- Name: objects_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.objects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.objects_id_seq OWNER TO postgres;

--
-- Name: objects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.objects_id_seq OWNED BY public.objects.id;


--
-- Name: owner_profiles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.owner_profiles (
    id integer NOT NULL,
    user_id integer NOT NULL,
    profile_name character varying(200) NOT NULL,
    legal_type character varying(20) NOT NULL,
    profile_data json NOT NULL,
    active_tags json NOT NULL,
    is_complete boolean,
    is_public boolean,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone
);


ALTER TABLE public.owner_profiles OWNER TO postgres;

--
-- Name: COLUMN owner_profiles.user_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.owner_profiles.user_id IS 'ID пользователя-владельца';


--
-- Name: COLUMN owner_profiles.profile_name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.owner_profiles.profile_name IS 'Название профиля';


--
-- Name: COLUMN owner_profiles.legal_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.owner_profiles.legal_type IS 'Тип: individual (ФЛ) или legal (ЮЛ)';


--
-- Name: COLUMN owner_profiles.profile_data; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.owner_profiles.profile_data IS 'Динамические поля профиля в формате {tag_key: value}';


--
-- Name: COLUMN owner_profiles.active_tags; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.owner_profiles.active_tags IS 'Список активных тегов профиля';


--
-- Name: COLUMN owner_profiles.is_complete; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.owner_profiles.is_complete IS 'Заполнен ли профиль полностью';


--
-- Name: COLUMN owner_profiles.is_public; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.owner_profiles.is_public IS 'Доступен ли профиль другим пользователям';


--
-- Name: owner_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.owner_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.owner_profiles_id_seq OWNER TO postgres;

--
-- Name: owner_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.owner_profiles_id_seq OWNED BY public.owner_profiles.id;


--
-- Name: planning_templates; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.planning_templates (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    owner_telegram_id integer NOT NULL,
    object_id integer,
    is_active boolean,
    is_public boolean,
    start_time character varying(5) NOT NULL,
    end_time character varying(5) NOT NULL,
    hourly_rate integer NOT NULL,
    repeat_type character varying(20),
    repeat_days character varying(20),
    repeat_interval integer,
    repeat_end_date timestamp without time zone,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.planning_templates OWNER TO postgres;

--
-- Name: COLUMN planning_templates.name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.planning_templates.name IS 'Название шаблона';


--
-- Name: COLUMN planning_templates.description; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.planning_templates.description IS 'Описание шаблона';


--
-- Name: COLUMN planning_templates.owner_telegram_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.planning_templates.owner_telegram_id IS 'Telegram ID владельца';


--
-- Name: COLUMN planning_templates.object_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.planning_templates.object_id IS 'ID объекта (null для универсальных шаблонов)';


--
-- Name: COLUMN planning_templates.is_active; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.planning_templates.is_active IS 'Активен ли шаблон';


--
-- Name: COLUMN planning_templates.is_public; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.planning_templates.is_public IS 'Публичный ли шаблон (для всех владельцев)';


--
-- Name: COLUMN planning_templates.start_time; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.planning_templates.start_time IS 'Время начала (HH:MM)';


--
-- Name: COLUMN planning_templates.end_time; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.planning_templates.end_time IS 'Время окончания (HH:MM)';


--
-- Name: COLUMN planning_templates.hourly_rate; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.planning_templates.hourly_rate IS 'Почасовая ставка';


--
-- Name: COLUMN planning_templates.repeat_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.planning_templates.repeat_type IS 'Тип повторения: none, daily, weekly, monthly';


--
-- Name: COLUMN planning_templates.repeat_days; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.planning_templates.repeat_days IS 'Дни недели для повторения (1,2,3,4,5,6,7)';


--
-- Name: COLUMN planning_templates.repeat_interval; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.planning_templates.repeat_interval IS 'Интервал повторения';


--
-- Name: COLUMN planning_templates.repeat_end_date; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.planning_templates.repeat_end_date IS 'Дата окончания повторения';


--
-- Name: COLUMN planning_templates.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.planning_templates.created_at IS 'Дата создания';


--
-- Name: COLUMN planning_templates.updated_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.planning_templates.updated_at IS 'Дата обновления';


--
-- Name: planning_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.planning_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.planning_templates_id_seq OWNER TO postgres;

--
-- Name: planning_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.planning_templates_id_seq OWNED BY public.planning_templates.id;


--
-- Name: shift_schedules; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.shift_schedules (
    id integer NOT NULL,
    user_id integer NOT NULL,
    object_id integer NOT NULL,
    planned_start timestamp with time zone NOT NULL,
    planned_end timestamp with time zone NOT NULL,
    status character varying(50),
    hourly_rate numeric(10,2),
    notes text,
    notification_sent boolean,
    actual_shift_id integer,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    auto_closed boolean DEFAULT false,
    time_slot_id integer
);


ALTER TABLE public.shift_schedules OWNER TO postgres;

--
-- Name: shift_schedules_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.shift_schedules_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.shift_schedules_id_seq OWNER TO postgres;

--
-- Name: shift_schedules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.shift_schedules_id_seq OWNED BY public.shift_schedules.id;


--
-- Name: shifts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.shifts (
    id integer NOT NULL,
    user_id integer NOT NULL,
    object_id integer NOT NULL,
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone,
    status character varying(50),
    start_coordinates character varying(100),
    end_coordinates character varying(100),
    total_hours numeric(5,2),
    hourly_rate numeric(10,2),
    total_payment numeric(10,2),
    notes text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    time_slot_id integer,
    schedule_id integer,
    is_planned boolean
);


ALTER TABLE public.shifts OWNER TO postgres;

--
-- Name: shifts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.shifts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.shifts_id_seq OWNER TO postgres;

--
-- Name: shifts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.shifts_id_seq OWNED BY public.shifts.id;


--
-- Name: tag_references; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tag_references (
    id integer NOT NULL,
    key character varying(100) NOT NULL,
    label character varying(200) NOT NULL,
    description text,
    category character varying(100) NOT NULL,
    data_type character varying(50) NOT NULL,
    is_required boolean,
    is_system boolean,
    is_active boolean,
    options json,
    validation_pattern character varying(500),
    validation_message character varying(200),
    sort_order integer,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone
);


ALTER TABLE public.tag_references OWNER TO postgres;

--
-- Name: COLUMN tag_references.key; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tag_references.key IS 'Ключ тега (например: owner_name, company_inn)';


--
-- Name: COLUMN tag_references.label; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tag_references.label IS 'Человекочитаемое название тега';


--
-- Name: COLUMN tag_references.description; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tag_references.description IS 'Подробное описание назначения тега';


--
-- Name: COLUMN tag_references.category; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tag_references.category IS 'Категория тега (owner, company, employee, system)';


--
-- Name: COLUMN tag_references.data_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tag_references.data_type IS 'Тип данных: text, email, date, number, select, textarea';


--
-- Name: COLUMN tag_references.is_required; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tag_references.is_required IS 'Обязательное ли поле';


--
-- Name: COLUMN tag_references.is_system; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tag_references.is_system IS 'Системный тег (автозаполняется)';


--
-- Name: COLUMN tag_references.is_active; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tag_references.is_active IS 'Активен ли тег для использования';


--
-- Name: COLUMN tag_references.options; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tag_references.options IS 'Список опций для select полей';


--
-- Name: COLUMN tag_references.validation_pattern; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tag_references.validation_pattern IS 'Regex паттерн для валидации';


--
-- Name: COLUMN tag_references.validation_message; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tag_references.validation_message IS 'Сообщение об ошибке валидации';


--
-- Name: COLUMN tag_references.sort_order; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.tag_references.sort_order IS 'Порядок сортировки в интерфейсе';


--
-- Name: tag_references_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tag_references_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tag_references_id_seq OWNER TO postgres;

--
-- Name: tag_references_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tag_references_id_seq OWNED BY public.tag_references.id;


--
-- Name: template_time_slots; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.template_time_slots (
    id integer NOT NULL,
    template_id integer NOT NULL,
    day_of_week integer NOT NULL,
    start_time character varying(5) NOT NULL,
    end_time character varying(5) NOT NULL,
    hourly_rate integer NOT NULL,
    is_active boolean
);


ALTER TABLE public.template_time_slots OWNER TO postgres;

--
-- Name: COLUMN template_time_slots.template_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.template_time_slots.template_id IS 'ID шаблона';


--
-- Name: COLUMN template_time_slots.day_of_week; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.template_time_slots.day_of_week IS 'День недели (0=Понедельник, 6=Воскресенье)';


--
-- Name: COLUMN template_time_slots.start_time; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.template_time_slots.start_time IS 'Время начала (HH:MM)';


--
-- Name: COLUMN template_time_slots.end_time; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.template_time_slots.end_time IS 'Время окончания (HH:MM)';


--
-- Name: COLUMN template_time_slots.hourly_rate; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.template_time_slots.hourly_rate IS 'Почасовая ставка';


--
-- Name: COLUMN template_time_slots.is_active; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.template_time_slots.is_active IS 'Активен ли слот';


--
-- Name: template_time_slots_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.template_time_slots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.template_time_slots_id_seq OWNER TO postgres;

--
-- Name: template_time_slots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.template_time_slots_id_seq OWNED BY public.template_time_slots.id;


--
-- Name: time_slots; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.time_slots (
    id integer NOT NULL,
    object_id integer NOT NULL,
    slot_date date NOT NULL,
    start_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL,
    hourly_rate numeric(10,2),
    max_employees integer,
    is_additional boolean,
    is_active boolean,
    notes text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.time_slots OWNER TO postgres;

--
-- Name: time_slots_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.time_slots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.time_slots_id_seq OWNER TO postgres;

--
-- Name: time_slots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.time_slots_id_seq OWNED BY public.time_slots.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    telegram_id bigint NOT NULL,
    username character varying(255),
    first_name character varying(255) NOT NULL,
    last_name character varying(255),
    phone character varying(20),
    role character varying(50) NOT NULL,
    is_active boolean,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    roles json DEFAULT '["applicant"]'::json NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: contract_templates id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contract_templates ALTER COLUMN id SET DEFAULT nextval('public.contract_templates_id_seq'::regclass);


--
-- Name: contract_versions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contract_versions ALTER COLUMN id SET DEFAULT nextval('public.contract_versions_id_seq'::regclass);


--
-- Name: contracts id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contracts ALTER COLUMN id SET DEFAULT nextval('public.contracts_id_seq'::regclass);


--
-- Name: objects id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.objects ALTER COLUMN id SET DEFAULT nextval('public.objects_id_seq'::regclass);


--
-- Name: owner_profiles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.owner_profiles ALTER COLUMN id SET DEFAULT nextval('public.owner_profiles_id_seq'::regclass);


--
-- Name: planning_templates id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.planning_templates ALTER COLUMN id SET DEFAULT nextval('public.planning_templates_id_seq'::regclass);


--
-- Name: shift_schedules id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shift_schedules ALTER COLUMN id SET DEFAULT nextval('public.shift_schedules_id_seq'::regclass);


--
-- Name: shifts id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shifts ALTER COLUMN id SET DEFAULT nextval('public.shifts_id_seq'::regclass);


--
-- Name: tag_references id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tag_references ALTER COLUMN id SET DEFAULT nextval('public.tag_references_id_seq'::regclass);


--
-- Name: template_time_slots id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.template_time_slots ALTER COLUMN id SET DEFAULT nextval('public.template_time_slots_id_seq'::regclass);


--
-- Name: time_slots id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.time_slots ALTER COLUMN id SET DEFAULT nextval('public.time_slots_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
9e47662cd158
\.


--
-- Data for Name: contract_templates; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.contract_templates (id, name, description, content, version, is_active, created_by, created_at, updated_at, is_public, fields_schema) FROM stdin;
1	Договор ГПХ с физлицом		<h1>ДОГОВОР ГРАЖДАНСКО-ПРАВОВОГО ХАРАКТЕРА 12</h1>\r\n\r\n<p><strong>Заказчик:</strong> {{ owner_name }} {{ owner_last_name }}</p>\r\n<p><strong>Исполнитель:</strong> {{ employee_name }}</p>\r\n\r\n<h2>Персональные данные исполнителя:</h2>\r\n<ul>\r\n<li>Дата рождения: {{ birth_date }}</li>\r\n<li>ИНН: {{ inn }}</li>\r\n<li>СНИЛС: {{ snils }}</li>\r\n<li>Паспорт: серия {{ passport_series }}, номер {{ passport_number }}</li>\r\n</ul>\r\n\r\n<h2>Предмет договора:</h2>\r\n<p>Исполнитель обязуется выполнить работы по обеспечению охраны объектов Заказчика.</p>\r\n\r\n<p><strong>Дата договора:</strong> {{ current_date }}</p>\r\n\r\n<p>Подписи сторон:</p>\r\n<p>Заказчик: _________________</p>\r\n<p>Исполнитель: _________________</p>	1.1	t	1	2025-09-07 15:45:00.18167+00	2025-09-10 08:13:11.310531+00	t	[{"key": "employee_name", "label": "\\u0424\\u0418\\u041e \\u0441\\u043e\\u0442\\u0440\\u0443\\u0434\\u043d\\u0438\\u043a\\u0430", "required": true, "type": "text"}, {"key": "birth_date", "label": "\\u0414\\u0430\\u0442\\u0430 \\u0440\\u043e\\u0436\\u0434\\u0435\\u043d\\u0438\\u044f", "required": true, "type": "date"}, {"key": "inn", "label": "\\u0418\\u041d\\u041d", "required": false, "type": "text"}, {"key": "snils", "label": "\\u0421\\u041d\\u0418\\u041b\\u0421", "required": false, "type": "text"}, {"key": "passport_series", "label": "\\u0421\\u0435\\u0440\\u0438\\u044f \\u043f\\u0430\\u0441\\u043f\\u043e\\u0440\\u0442\\u0430", "required": false, "type": "text"}, {"key": "passport_number", "label": "\\u041d\\u043e\\u043c\\u0435\\u0440 \\u043f\\u0430\\u0441\\u043f\\u043e\\u0440\\u0442\\u0430", "required": false, "type": "text"}]
2	Трудовой договор 2		Трудовой договор {{ dog_Num }}	1.0	t	1	2025-09-10 07:57:23.247224+00	2025-09-10 08:14:24.987467+00	f	[{"key": "dog_Num", "label": "\\u041d\\u043e\\u043c\\u0435\\u0440 \\u0434\\u043e\\u0433\\u043e\\u0432\\u043e\\u0440\\u0430", "type": "text", "required": false, "options": ""}]
\.


--
-- Data for Name: contract_versions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.contract_versions (id, contract_id, version_number, content, changes_description, created_by, created_at) FROM stdin;
1	1	1.0	договорились	Договор расторгнут. Причина: нет	1	2025-09-07 14:22:59.616933+00
2	3	1.0	ДОГОВОР ГРАЖДАНСКО-ПРАВОВОГО ХАРАКТЕРА 1\r\n\r\n\r\n\r\nЗаказчик: {{ owner_name }} {{ owner_last_name }}\r\n\r\n\r\nИсполнитель: {{ employee_name }}\r\n\r\n\r\n\r\nПерсональные данные исполнителя:\r\n\r\n\r\n\r\n\r\n\r\n\r\nПредмет договора:\r\n\r\n\r\nИсполнитель обязуется выполнить работы по обеспечению охраны объектов Заказчика.\r\n\r\n\r\n\r\nДата договора: {{ current_date }}\r\n\r\n\r\n\r\nПодписи сторон:\r\n\r\n\r\nЗаказчик: _________________\r\n\r\n\r\nИсполнитель: _________________\r\n	Договор расторгнут. Причина: обоюдка	1	2025-09-10 09:27:16.220483+00
3	2	1.0	555	Договор расторгнут. Причина: не нужно	1	2025-09-10 09:35:54.859798+00
5	6	1.0		Договор расторгнут. Причина: дэжлор	1	2025-09-10 09:56:34.689757+00
6	7	1.0		Договор расторгнут. Причина: Расторжение по кнопке	1	2025-09-10 11:04:00.991319+00
7	8	1.0		Договор расторгнут. Причина: 1	1	2025-09-10 11:04:56.502295+00
8	9	1.0		Договор расторгнут. Причина: Расторжение по кнопке	1	2025-09-10 11:10:16.582269+00
9	10	1.0		Договор расторгнут. Причина: 4	1	2025-09-10 11:13:21.576887+00
10	11	1.0		Договор расторгнут. Причина: Расторжение по кнопке	1	2025-09-10 11:13:56.079286+00
11	12	1.0		Договор расторгнут. Причина: 43цу5кнаегпо	1	2025-09-10 11:15:49.315847+00
\.


--
-- Data for Name: contracts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.contracts (id, contract_number, owner_id, employee_id, template_id, title, content, hourly_rate, start_date, end_date, status, is_active, allowed_objects, created_at, updated_at, signed_at, terminated_at, "values") FROM stdin;
2	001-2025-000002	1	6	1	Устный договор 2	555	1555	2025-09-06 00:00:00+00	\N	terminated	f	[1]	2025-09-07 14:40:29.384395+00	2025-09-10 09:35:54.836038+00	2025-09-07 15:04:12.736704+00	2025-09-10 09:35:54.838162+00	\N
1	001-2025-000001	1	6	\N	Устный договор	договорились	255	2025-09-07 00:00:00+00	2025-12-31 00:00:00+00	terminated	f	[1]	2025-09-07 13:51:04.68389+00	2025-09-07 14:22:59.58946+00	\N	2025-09-07 14:22:59.592262+00	\N
4	003-2025-000001	3	4	1	Договор ГПХ №СХ-5 от 09.09.2025	ДОГОВОР ГРАЖДАНСКО-ПРАВОВОГО ХАРАКТЕРА\r\n\r\nЗаказчик:  + tagKey +   + tagKey + \r\nИсполнитель: Новикова Анна Юрьевна\r\n\r\nПерсональные данные исполнителя:\r\n\r\nДата рождения: 1986-03-28\r\nИНН: 618253635211\r\nСНИЛС: 128-225-863 80\r\nПаспорт: серия 6066 , номер 333666\r\n\r\n\r\nПредмет договора:\r\nИсполнитель обязуется выполнить работы по обеспечению охраны объектов Заказчика.\r\n\r\nДата договора:  + tagKey + \r\n\r\nПодписи сторон:\r\nЗаказчик: _________________\r\nИсполнитель: _________________	250	2025-09-09 00:00:00+00	2025-12-09 00:00:00+00	active	t	[11, 12]	2025-09-09 12:54:26.088859+00	2025-09-09 13:23:32.974693+00	\N	\N	{"employee_name": "\\u041d\\u043e\\u0432\\u0438\\u043a\\u043e\\u0432\\u0430 \\u0410\\u043d\\u043d\\u0430 \\u042e\\u0440\\u044c\\u0435\\u0432\\u043d\\u0430", "birth_date": "1986-03-28", "inn": "618253635211", "snils": "128-225-863 80", "passport_series": "6066 ", "passport_number": "333666"}
5	001-2025-000004	1	6	\N	ГПХ на 432	\N	150	2025-09-10 00:00:00+00	\N	active	t	[6]	2025-09-10 08:56:34.038344+00	\N	\N	\N	null
3	001-2025-000003	1	7	1	ГПХ ФЛ	ДОГОВОР ГРАЖДАНСКО-ПРАВОВОГО ХАРАКТЕРА 1\r\n\r\n\r\n\r\nЗаказчик: {{ owner_name }} {{ owner_last_name }}\r\n\r\n\r\nИсполнитель: {{ employee_name }}\r\n\r\n\r\n\r\nПерсональные данные исполнителя:\r\n\r\n\r\n\r\n\r\n\r\n\r\nПредмет договора:\r\n\r\n\r\nИсполнитель обязуется выполнить работы по обеспечению охраны объектов Заказчика.\r\n\r\n\r\n\r\nДата договора: {{ current_date }}\r\n\r\n\r\n\r\nПодписи сторон:\r\n\r\n\r\nЗаказчик: _________________\r\n\r\n\r\nИсполнитель: _________________\r\n	124	2025-09-09 00:00:00+00	\N	terminated	f	[1]	2025-09-09 07:52:55.403438+00	2025-09-10 09:27:16.194089+00	2025-09-10 08:58:33.765552+00	2025-09-10 09:27:16.196526+00	{"employee_name": "\\u0422\\u0435\\u0441\\u0442\\u043e\\u0432\\u044b\\u0439 \\u0422\\u0435\\u0441\\u0442", "birth_date": "2000-12-12", "inn": "1234567890", "passport_series": "0987", "passport_number": "098765"}
6	001-2025-000005	1	6	\N	ГПХ на 25	\N	\N	2025-09-10 00:00:00+00	\N	terminated	f	[9]	2025-09-10 09:38:08.177369+00	2025-09-10 09:56:34.663575+00	\N	2025-09-10 09:56:34.666559+00	null
7	001-2025-000006	1	6	\N	ГПХ на 25	\N	111	2025-09-10 00:00:00+00	\N	terminated	f	[9]	2025-09-10 11:03:47.991756+00	2025-09-10 11:04:00.965606+00	\N	2025-09-10 11:04:00.968013+00	null
8	001-2025-000007	1	6	\N	ГПХ на 25	\N	222	2025-09-10 00:00:00+00	\N	terminated	f	[9]	2025-09-10 11:04:42.438716+00	2025-09-10 11:04:56.475806+00	\N	2025-09-10 11:04:56.479053+00	null
9	001-2025-000008	1	6	\N	ГПХ на 25	\N	333	2025-09-10 00:00:00+00	\N	terminated	f	[9]	2025-09-10 11:09:40.780613+00	2025-09-10 11:10:16.556212+00	\N	2025-09-10 11:10:16.558978+00	null
10	001-2025-000009	1	6	\N	ГПХ на 25	\N	444	2025-09-10 00:00:00+00	\N	terminated	f	[9]	2025-09-10 11:12:54.765693+00	2025-09-10 11:13:21.551315+00	\N	2025-09-10 11:13:21.553942+00	null
11	001-2025-000010	1	6	\N	ГПХ на 255	\N	555	2025-09-10 00:00:00+00	\N	terminated	f	[9]	2025-09-10 11:13:44.044574+00	2025-09-10 11:13:56.055115+00	\N	2025-09-10 11:13:56.057453+00	null
12	001-2025-000011	1	6	\N	ГПХ на 25	\N	555	2025-09-10 00:00:00+00	\N	terminated	f	[9]	2025-09-10 11:15:38.470274+00	2025-09-10 11:15:49.290192+00	\N	2025-09-10 11:15:49.293097+00	null
13	001-2025-000012	1	6	\N	ТТТ	\N	100	2025-09-10 00:00:00+00	\N	active	t	[9]	2025-09-10 17:33:25.298831+00	\N	\N	\N	null
\.


--
-- Data for Name: objects; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.objects (id, name, owner_id, address, coordinates, opening_time, closing_time, hourly_rate, required_employees, is_active, created_at, updated_at, max_distance_meters, auto_close_minutes, available_for_applicants, work_days_mask, schedule_repeat_weeks, timezone) FROM stdin;
2	Планерная	2	микрорайон Планерная, 15, Химки, Московская область	55.920790, 37.368505	10:00:00	22:00:00	250.00	\N	t	2025-08-28 09:42:55.080554+00	2025-08-28 09:43:30.306657+00	100	60	\N	31	1	Europe/Moscow
23	О366	1	РнД, Туполева 9А	47.280937,39.804485	09:00:00	21:00:00	200.00	\N	t	2025-09-12 08:33:34.011039+00	2025-09-12 08:33:34.011039+00	150	60	t	127	1	Europe/Moscow
9	Аксай	1	ул. Тестовая, 1	47.271321,39.861465	09:00:00	21:00:00	150.00	\N	t	2025-09-07 06:19:48.647284+00	2025-09-14 10:38:33.706347+00	500	60	f	63	1	Europe/Moscow
6	Озон 432	1	40летия Победы	47.238865,39.830658	09:00:00	21:00:00	150.00	\N	t	2025-09-06 07:55:47.697166+00	2025-09-08 18:24:51.07005+00	500	60	\N	31	1	Europe/Moscow
11	Сходненская 15	3	Путилково, Сходненская 15	55.87689,37.391305	09:00:00	21:00:00	250.00	\N	t	2025-09-09 12:33:16.272472+00	2025-09-09 12:33:16.272472+00	300	30	f	31	1	Europe/Moscow
12	Сходненская 17	3	путилково, сходненская 17	55.877036,37.389077	10:00:00	22:00:00	300.00	\N	t	2025-09-09 12:41:57.857138+00	2025-09-09 12:41:57.857138+00	500	60	f	31	1	Europe/Moscow
24	Тест	6	Пррррр	55.5565,37.6134	09:00:00	18:00:00	150.00	\N	t	2025-09-14 13:30:20.893612+00	2025-09-14 13:30:20.893612+00	200	54	f	31	1	Europe/Moscow
\.


--
-- Data for Name: owner_profiles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.owner_profiles (id, user_id, profile_name, legal_type, profile_data, active_tags, is_complete, is_public, created_at, updated_at) FROM stdin;
1	1	Мой профиль	individual	{"owner_name": "\\u0412\\u0430\\u0441\\u0438\\u043b\\u0438\\u0439", "owner_last_name": "\\u041f\\u0443\\u043f\\u043a\\u0438\\u043d"}	["owner_name", "owner_last_name"]	t	f	2025-09-09 10:26:43.660485+00	2025-09-09 10:26:43.660485+00
\.


--
-- Data for Name: planning_templates; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.planning_templates (id, name, description, owner_telegram_id, object_id, is_active, is_public, start_time, end_time, hourly_rate, repeat_type, repeat_days, repeat_interval, repeat_end_date, created_at, updated_at) FROM stdin;
3	ffwg		1220971779	\N	f	f	09:00	18:00	123	daily		1	\N	2025-09-07 07:59:34.439198	2025-09-07 08:16:06.739731
1	КаждыйДень9-21_250Р		1220971779	\N	t	t	09:00	21:00	250	daily		1	\N	2025-09-07 07:33:16.051234	2025-09-10 12:01:11.016363
4	КаждыйДень10-22_250Р		1220971779	\N	t	f	10:00	22:00	250	daily		1	\N	2025-09-10 12:04:16.841317	2025-09-10 12:04:16.841317
\.


--
-- Data for Name: shift_schedules; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.shift_schedules (id, user_id, object_id, planned_start, planned_end, status, hourly_rate, notes, notification_sent, actual_shift_id, created_at, updated_at, auto_closed, time_slot_id) FROM stdin;
12	3	11	2025-09-10 09:00:00+00	2025-09-10 21:00:00+00	planned	250.00	Запланировано через бота	f	\N	2025-09-09 13:14:15.922045+00	2025-09-09 13:14:15.922045+00	f	189
13	3	11	2025-09-15 09:00:00+00	2025-09-15 21:00:00+00	planned	250.00	Запланировано через бота	f	\N	2025-09-09 13:14:54.434028+00	2025-09-09 13:14:54.434028+00	f	180
14	3	12	2025-09-12 10:00:00+00	2025-09-12 22:00:00+00	planned	300.00	Запланировано через бота	f	\N	2025-09-09 13:20:37.128445+00	2025-09-09 13:20:37.128445+00	f	198
11	1	6	2025-09-19 09:47:00+00	2025-09-19 21:00:00+00	cancelled	254.00	Запланировано через бота	f	\N	2025-09-08 12:39:45.131848+00	2025-09-10 06:40:56.176364+00	f	166
17	6	9	2025-09-13 09:00:00+00	2025-09-13 21:00:00+00	planned	150.00	Запланировано через бота	f	\N	2025-09-12 13:59:13.640372+00	2025-09-12 13:59:13.640372+00	f	765
20	4	12	2025-09-17 10:00:00+00	2025-09-17 22:00:00+00	planned	300.00	Запланировано через бота	f	\N	2025-09-13 11:48:45.251538+00	2025-09-13 11:48:45.251538+00	f	766
21	4	11	2025-09-14 09:00:00+00	2025-09-14 21:00:00+00	planned	250.00	Запланировано через бота	f	\N	2025-09-13 11:49:36.846145+00	2025-09-13 11:49:36.846145+00	f	186
18	6	6	2025-09-15 09:00:00+00	2025-09-15 21:00:00+00	cancelled	150.00	Запланировано через бота	f	\N	2025-09-12 17:59:11.301969+00	2025-09-14 06:27:25.450325+00	f	739
22	6	9	2025-09-14 09:00:00+00	2025-09-14 21:00:00+00	cancelled	150.00	Запланировано через бота	f	\N	2025-09-14 06:33:13.588111+00	2025-09-14 07:10:56.800692+00	f	767
15	6	6	2025-09-12 09:00:00+00	2025-09-12 21:00:00+00	cancelled	150.00	Запланировано через бота	f	\N	2025-09-12 08:20:26.345887+00	2025-09-14 13:06:16.634339+00	f	38
16	6	6	2025-09-13 09:00:00+00	2025-09-13 21:00:00+00	cancelled	150.00	Запланировано через бота	f	\N	2025-09-12 08:22:03.314343+00	2025-09-14 13:06:20.126097+00	f	41
23	6	9	2025-09-14 09:00:00+00	2025-09-14 21:00:00+00	planned	150.00	Запланировано через бота	f	\N	2025-09-14 13:06:30.560861+00	2025-09-14 13:06:30.560861+00	f	767
24	6	9	2025-09-15 09:00:00+00	2025-09-15 21:00:00+00	planned	500.00	Запланировано через бота	f	\N	2025-09-14 13:06:39.14675+00	2025-09-14 13:06:39.14675+00	f	734
25	6	9	2025-09-16 09:00:00+00	2025-09-16 21:00:00+00	planned	500.00	Запланировано через бота	f	\N	2025-09-14 13:31:15.158892+00	2025-09-14 13:31:15.158892+00	f	735
19	1	6	2025-09-12 19:01:02.971597+00	2025-09-12 21:01:02.971597+00	cancelled	500.00	\N	\N	\N	2025-09-12 18:01:02.971597+00	2025-09-17 13:09:53.647101+00	f	\N
\.


--
-- Data for Name: shifts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.shifts (id, user_id, object_id, start_time, end_time, status, start_coordinates, end_coordinates, total_hours, hourly_rate, total_payment, notes, created_at, updated_at, time_slot_id, schedule_id, is_planned) FROM stdin;
14	1	6	2025-09-06 11:33:58.410739+00	2025-09-06 11:35:50.13111+00	completed	47.238898,39.830711	47.238898,39.830711	0.03	150.00	4.50	Закрыта пользователем в 11:35:50	2025-09-06 11:33:58.406573+00	2025-09-06 11:35:50.129679+00	\N	\N	\N
15	1	6	2025-09-07 15:00:00+00	2025-09-07 21:00:00+00	cancelled	\N	\N	\N	150.00	\N	Запланировано через бота	2025-09-06 12:31:06.048664+00	2025-09-06 12:31:18.975776+00	33	\N	\N
21	1	6	2025-09-08 09:04:30.063067+00	2025-09-08 18:22:05.644807+00	completed	47.238898,39.830711	\N	\N	150.00	\N	\N	2025-09-08 09:04:30.059146+00	2025-09-08 18:22:05.644812+00	\N	\N	f
23	3	11	2025-09-09 13:03:43.048161+00	2025-09-09 13:25:45.097564+00	completed	55.876966,37.391468	55.876826,37.391501	0.37	250.00	92.50	Закрыта пользователем в 13:25:45	2025-09-09 13:03:43.044996+00	2025-09-09 13:25:45.096633+00	\N	\N	f
22	1	6	2025-09-09 07:38:47.415768+00	2025-09-09 16:35:34.636257+00	completed	47.238898,39.830711	\N	\N	150.00	\N	\N	2025-09-09 07:38:47.412594+00	2025-09-09 16:35:34.636262+00	\N	\N	f
25	6	6	2025-09-12 08:03:42.976069+00	2025-09-12 08:19:01.730196+00	completed	47.238898,39.830711	47.238898,39.830711	0.26	150.00	39.00	Закрыта пользователем в 08:19:01	2025-09-12 08:03:42.971525+00	2025-09-12 08:19:01.728815+00	\N	\N	f
26	6	6	2025-09-12 08:20:36.347874+00	2025-09-12 16:29:03.72288+00	completed	47.238898,39.830711	47.238898,39.830711	8.14	150.00	1221.00	Закрыта пользователем в 16:29:03	2025-09-12 08:20:36.343669+00	2025-09-12 16:29:03.721629+00	\N	\N	f
24	3	12	2025-09-09 13:26:11.040752+00	2025-09-13 11:29:10.8754+00	completed	55.876826,37.391501	55.876966,37.391468	94.05	300.00	28215.00	Закрыта пользователем в 11:29:10	2025-09-09 13:26:11.035955+00	2025-09-13 11:29:10.866212+00	\N	\N	f
27	6	9	2025-09-14 06:58:06.018942+00	2025-09-14 07:02:51.883423+00	completed	47.271969,39.861781	47.271969,39.861781	0.08	500.00	40.00	Закрыта пользователем в 07:02:51	2025-09-14 06:58:06.01244+00	2025-09-14 07:02:51.882423+00	\N	\N	f
28	6	9	2025-09-14 07:03:52.007861+00	2025-09-14 07:07:37.8915+00	completed	47.271969,39.861781	47.271969,39.861781	0.06	150.00	9.00	Закрыта пользователем в 07:07:37	2025-09-14 07:03:51.976104+00	2025-09-14 07:07:37.890329+00	767	22	t
29	6	9	2025-09-14 07:09:39.434169+00	2025-09-14 07:10:47.803917+00	completed	47.271951,39.861758	47.271969,39.861781	0.02	150.00	3.00	Закрыта пользователем в 07:10:47	2025-09-14 07:09:39.403022+00	2025-09-14 07:10:47.802391+00	767	22	t
30	6	9	2025-09-14 07:25:45.406804+00	2025-09-14 07:30:43.48438+00	completed	47.271969,39.861781	47.271969,39.861781	0.08	500.00	40.00	Закрыта пользователем в 07:30:43	2025-09-14 07:25:45.40258+00	2025-09-14 07:30:43.483228+00	\N	\N	f
32	1	9	2025-09-14 08:15:52.154845+00	2025-09-14 09:34:24.993222+00	completed	47.271987,39.861803	47.271969,39.861781	1.31	150.00	196.50	Закрыта пользователем в 09:34:24	2025-09-14 08:15:52.110293+00	2025-09-14 09:34:24.992145+00	\N	\N	f
31	6	9	2025-09-14 07:32:08.736635+00	2025-09-14 13:05:37.78231+00	completed	47.271969,39.861781	47.271969,39.861781	5.56	150.00	834.00	Закрыта пользователем в 13:05:37	2025-09-14 07:32:08.704761+00	2025-09-14 13:05:37.781214+00	\N	\N	f
33	6	9	2025-09-14 13:06:54.292406+00	2025-09-14 13:16:24.460201+00	completed	47.271969,39.861781	47.271969,39.861781	0.16	150.00	24.00	Закрыта пользователем в 13:16:24	2025-09-14 13:06:54.261871+00	2025-09-14 13:16:24.459196+00	767	23	t
34	6	9	2025-09-14 13:16:34.710181+00	2025-09-14 13:19:25.37287+00	completed	47.271969,39.861781	47.271951,39.861758	0.05	150.00	7.50	Закрыта пользователем в 13:19:25	2025-09-14 13:16:34.678724+00	2025-09-14 13:19:25.371879+00	767	23	t
35	6	9	2025-09-14 13:19:42.204175+00	\N	cancelled	47.271951,39.861758	\N	\N	150.00	\N	\N	2025-09-14 13:19:42.174555+00	2025-09-16 13:46:33.896113+00	767	23	t
\.


--
-- Data for Name: spatial_ref_sys; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.spatial_ref_sys (srid, auth_name, auth_srid, srtext, proj4text) FROM stdin;
\.


--
-- Data for Name: tag_references; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tag_references (id, key, label, description, category, data_type, is_required, is_system, is_active, options, validation_pattern, validation_message, sort_order, created_at, updated_at) FROM stdin;
1	current_date	Текущая дата	Автоматически подставляется текущая дата в формате ДД.ММ.ГГГГ	system	text	f	t	t	\N	\N	\N	1000	2025-09-09 10:13:28.803854+00	\N
2	current_time	Текущее время	Автоматически подставляется текущее время в формате ЧЧ:ММ	system	text	f	t	t	\N	\N	\N	1001	2025-09-09 10:13:28.803854+00	\N
3	current_year	Текущий год	Автоматически подставляется текущий год в формате ГГГГ	system	text	f	t	t	\N	\N	\N	1002	2025-09-09 10:13:28.803854+00	\N
4	owner_name	Имя владельца	Имя владельца бизнеса/заказчика	owner	text	t	f	t	\N	\N	\N	100	2025-09-09 10:13:28.803854+00	\N
5	owner_last_name	Фамилия владельца	Фамилия владельца бизнеса/заказчика	owner	text	t	f	t	\N	\N	\N	101	2025-09-09 10:13:28.803854+00	\N
6	owner_middle_name	Отчество владельца	Отчество владельца бизнеса/заказчика	owner	text	f	f	t	\N	\N	\N	102	2025-09-09 10:13:28.803854+00	\N
7	owner_full_name	ФИО владельца полностью	Полное ФИО владельца в формате "Фамилия Имя Отчество"	owner	text	f	f	t	\N	\N	\N	103	2025-09-09 10:13:28.803854+00	\N
8	owner_birth_date	Дата рождения владельца	Дата рождения владельца	owner	date	f	f	t	\N	\N	\N	104	2025-09-09 10:13:28.803854+00	\N
9	owner_inn	ИНН владельца	Индивидуальный налоговый номер владельца	owner	text	f	f	t	\N	^\\d{10}|\\d{12}$	ИНН должен содержать 10 или 12 цифр	105	2025-09-09 10:13:28.803854+00	\N
10	owner_snils	СНИЛС владельца	Страховой номер индивидуального лицевого счета владельца	owner	text	f	f	t	\N	^\\d{3}-\\d{3}-\\d{3} \\d{2}$	СНИЛС должен быть в формате XXX-XXX-XXX XX	106	2025-09-09 10:13:28.803854+00	\N
11	owner_phone	Телефон владельца	Контактный телефон владельца	owner	text	f	f	t	\N	^\\+7\\d{10}$	Телефон должен быть в формате +7XXXXXXXXXX	107	2025-09-09 10:13:28.803854+00	\N
12	owner_email	Email владельца	Электронная почта владельца	owner	email	f	f	t	\N	\N	\N	108	2025-09-09 10:13:28.803854+00	\N
13	company_name	Название компании	Полное наименование организации	company	text	f	f	t	\N	\N	\N	200	2025-09-09 10:13:28.803854+00	\N
14	company_short_name	Краткое название компании	Сокращенное наименование организации	company	text	f	f	t	\N	\N	\N	201	2025-09-09 10:13:28.803854+00	\N
15	company_inn	ИНН компании	Индивидуальный налоговый номер организации	company	text	f	f	t	\N	^\\d{10}$	ИНН организации должен содержать 10 цифр	202	2025-09-09 10:13:28.803854+00	\N
16	company_kpp	КПП компании	Код причины постановки на учет	company	text	f	f	t	\N	^\\d{9}$	КПП должен содержать 9 цифр	203	2025-09-09 10:13:28.803854+00	\N
17	company_ogrn	ОГРН компании	Основной государственный регистрационный номер	company	text	f	f	t	\N	^\\d{13}|\\d{15}$	ОГРН должен содержать 13 или 15 цифр	204	2025-09-09 10:13:28.803854+00	\N
18	company_address	Адрес компании	Юридический адрес организации	company	textarea	f	f	t	\N	\N	\N	205	2025-09-09 10:13:28.803854+00	\N
19	company_bank_name	Название банка	Наименование банка для расчетного счета	company	text	f	f	t	\N	\N	\N	206	2025-09-09 10:13:28.803854+00	\N
20	company_bank_account	Расчетный счет	Номер расчетного счета в банке	company	text	f	f	t	\N	^\\d{20}$	Расчетный счет должен содержать 20 цифр	207	2025-09-09 10:13:28.803854+00	\N
21	company_bank_bik	БИК банка	Банковский идентификационный код	company	text	f	f	t	\N	^\\d{9}$	БИК должен содержать 9 цифр	208	2025-09-09 10:13:28.803854+00	\N
22	company_bank_corr_account	Корреспондентский счет	Корреспондентский счет банка	company	text	f	f	t	\N	^\\d{20}$	Корреспондентский счет должен содержать 20 цифр	209	2025-09-09 10:13:28.803854+00	\N
23	employee_name	Имя сотрудника	Имя сотрудника/исполнителя	employee	text	t	f	t	\N	\N	\N	300	2025-09-09 10:13:28.803854+00	\N
24	employee_last_name	Фамилия сотрудника	Фамилия сотрудника/исполнителя	employee	text	f	f	t	\N	\N	\N	301	2025-09-09 10:13:28.803854+00	\N
25	employee_middle_name	Отчество сотрудника	Отчество сотрудника/исполнителя	employee	text	f	f	t	\N	\N	\N	302	2025-09-09 10:13:28.803854+00	\N
26	birth_date	Дата рождения сотрудника	Дата рождения сотрудника	employee	date	f	f	t	\N	\N	\N	303	2025-09-09 10:13:28.803854+00	\N
27	inn	ИНН сотрудника	Индивидуальный налоговый номер сотрудника	employee	text	f	f	t	\N	^\\d{12}$	ИНН физического лица должен содержать 12 цифр	304	2025-09-09 10:13:28.803854+00	\N
28	snils	СНИЛС сотрудника	Страховой номер индивидуального лицевого счета сотрудника	employee	text	f	f	t	\N	^\\d{3}-\\d{3}-\\d{3} \\d{2}$	СНИЛС должен быть в формате XXX-XXX-XXX XX	305	2025-09-09 10:13:28.803854+00	\N
29	passport_series	Серия паспорта	Серия паспорта сотрудника	employee	text	f	f	t	\N	^\\d{4}$	Серия паспорта должна содержать 4 цифры	306	2025-09-09 10:13:28.803854+00	\N
30	passport_number	Номер паспорта	Номер паспорта сотрудника	employee	text	f	f	t	\N	^\\d{6}$	Номер паспорта должен содержать 6 цифр	307	2025-09-09 10:13:28.803854+00	\N
31	passport_issued_by	Кем выдан паспорт	Орган, выдавший паспорт	employee	textarea	f	f	t	\N	\N	\N	308	2025-09-09 10:13:28.803854+00	\N
32	passport_issue_date	Дата выдачи паспорта	Дата выдачи паспорта	employee	date	f	f	t	\N	\N	\N	309	2025-09-09 10:13:28.803854+00	\N
33	passport_department_code	Код подразделения	Код подразделения, выдавшего паспорт	employee	text	f	f	t	\N	^\\d{3}-\\d{3}$	Код подразделения должен быть в формате XXX-XXX	310	2025-09-09 10:13:28.803854+00	\N
34	registration_address	Адрес регистрации	Адрес регистрации сотрудника по паспорту	employee	textarea	f	f	t	\N	\N	\N	311	2025-09-09 10:13:28.803854+00	\N
35	employee_phone	Телефон сотрудника	Контактный телефон сотрудника	employee	text	f	f	t	\N	^\\+7\\d{10}$	Телефон должен быть в формате +7XXXXXXXXXX	312	2025-09-09 10:13:28.803854+00	\N
36	employee_email	Email сотрудника	Электронная почта сотрудника	employee	email	f	f	t	\N	\N	\N	313	2025-09-09 10:13:28.803854+00	\N
37	contract_number	Номер договора	Номер заключаемого договора	contract	text	f	f	t	\N	\N	\N	400	2025-09-09 10:13:28.803854+00	\N
38	contract_date	Дата договора	Дата заключения договора	contract	date	f	f	t	\N	\N	\N	401	2025-09-09 10:13:28.803854+00	\N
39	contract_start_date	Дата начала действия	Дата начала действия договора	contract	date	f	f	t	\N	\N	\N	402	2025-09-09 10:13:28.803854+00	\N
40	contract_end_date	Дата окончания	Дата окончания действия договора	contract	date	f	f	t	\N	\N	\N	403	2025-09-09 10:13:28.803854+00	\N
41	contract_amount	Сумма договора	Общая сумма по договору	contract	number	f	f	t	\N	\N	\N	404	2025-09-09 10:13:28.803854+00	\N
42	hourly_rate	Часовая ставка	Размер оплаты за час работы	contract	number	f	f	t	\N	\N	\N	405	2025-09-09 10:13:28.803854+00	\N
43	work_description	Описание работ	Подробное описание выполняемых работ	contract	textarea	f	f	t	\N	\N	\N	406	2025-09-09 10:13:28.803854+00	\N
\.


--
-- Data for Name: template_time_slots; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.template_time_slots (id, template_id, day_of_week, start_time, end_time, hourly_rate, is_active) FROM stdin;
\.


--
-- Data for Name: time_slots; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.time_slots (id, object_id, slot_date, start_time, end_time, hourly_rate, max_employees, is_additional, is_active, notes, created_at, updated_at) FROM stdin;
770	2	2026-01-05	10:00:00	22:00:00	250.00	1	f	f	\N	2025-09-14 11:27:18.383435+00	2025-09-17 14:11:06.154233+00
619	6	2025-09-16	09:00:00	21:00:00	150.00	1	f	t		2025-09-10 17:29:11.327237+00	2025-09-10 17:29:11.327237+00
623	23	2025-09-15	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
624	23	2025-09-16	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
625	23	2025-09-17	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
626	23	2025-09-18	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
627	23	2025-09-19	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
628	23	2025-09-20	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
34	6	2025-09-08	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-06 12:11:28.897636+00	2025-09-06 12:11:28.897636+00
35	6	2025-09-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-06 12:11:28.897636+00	2025-09-06 12:11:28.897636+00
36	6	2025-09-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-06 12:11:28.897636+00	2025-09-06 12:11:28.897636+00
37	6	2025-09-11	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-06 12:11:28.897636+00	2025-09-06 12:11:28.897636+00
32	6	2025-09-06	09:00:00	21:00:00	150.00	1	f	f	\N	2025-09-06 12:11:28.897636+00	2025-09-06 12:17:48.290273+00
620	23	2025-09-12	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 09:40:18.069332+00
621	23	2025-09-13	09:00:00	21:00:00	\N	2	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 11:41:54.475528+00
622	23	2025-09-14	09:00:00	21:00:00	\N	2	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 11:41:54.475528+00
33	6	2025-09-07	15:01:00	21:00:00	220.00	2	f	f	\N	2025-09-06 12:11:28.897636+00	2025-09-10 05:59:08.09134+00
629	23	2025-09-21	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
630	23	2025-09-22	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
631	23	2025-09-23	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
41	6	2025-09-13	09:00:00	21:00:00	150.00	1	f	t		2025-09-07 07:08:08.905277+00	2025-09-07 07:08:08.905277+00
38	6	2025-09-12	09:00:00	21:00:00	150.00	2	f	t	\N	2025-09-06 12:11:28.897636+00	2025-09-12 16:53:00.687014+00
632	23	2025-09-24	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
61	9	2025-09-08	09:00:00	12:00:00	254.00	1	f	f		2025-09-08 11:17:27.08624+00	2025-09-08 11:34:17.936418+00
60	9	2025-09-11	09:00:00	21:00:00	500.00	1	f	f		2025-09-08 10:39:19.861153+00	2025-09-08 11:34:17.965077+00
62	9	2025-09-20	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:53.564704+00	2025-09-08 11:34:18.02217+00
63	9	2025-09-21	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:53.599455+00	2025-09-08 11:34:18.050652+00
64	9	2025-09-22	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:53.627557+00	2025-09-08 11:34:18.079262+00
65	9	2025-09-23	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:53.655572+00	2025-09-08 11:34:18.107543+00
66	9	2025-09-24	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:53.684158+00	2025-09-08 11:34:18.13596+00
67	9	2025-09-25	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:53.712422+00	2025-09-08 11:34:18.163868+00
68	9	2025-09-26	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:53.740281+00	2025-09-08 11:34:18.192057+00
69	9	2025-09-27	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:53.767919+00	2025-09-08 11:34:18.220464+00
70	9	2025-09-28	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:53.795704+00	2025-09-08 11:34:18.247988+00
71	9	2025-09-29	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:53.823843+00	2025-09-08 11:34:18.27591+00
72	9	2025-09-30	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:53.852171+00	2025-09-08 11:34:18.304037+00
73	9	2025-10-01	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:53.880656+00	2025-09-08 11:34:18.331758+00
74	9	2025-10-02	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:53.909148+00	2025-09-08 11:34:18.359713+00
75	9	2025-10-03	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:53.937251+00	2025-09-08 11:34:18.387767+00
76	9	2025-10-04	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:53.965738+00	2025-09-08 11:34:18.415589+00
77	9	2025-10-05	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:53.993549+00	2025-09-08 11:34:18.443337+00
79	9	2025-10-07	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.049401+00	2025-09-08 11:34:18.499465+00
80	9	2025-10-08	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.07744+00	2025-09-08 11:34:18.527386+00
81	9	2025-10-09	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.106252+00	2025-09-08 11:34:18.555217+00
82	9	2025-10-10	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.134019+00	2025-09-08 11:34:18.583066+00
83	9	2025-10-11	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.164122+00	2025-09-08 11:34:18.610924+00
84	9	2025-10-12	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.193775+00	2025-09-08 11:34:18.639582+00
85	9	2025-10-13	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.224432+00	2025-09-08 11:34:18.667706+00
86	9	2025-10-14	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.255593+00	2025-09-08 11:34:18.695879+00
87	9	2025-10-15	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.287754+00	2025-09-08 11:34:18.724158+00
88	9	2025-10-16	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.319351+00	2025-09-08 11:34:18.752778+00
89	9	2025-10-17	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.351008+00	2025-09-08 11:34:18.78076+00
90	9	2025-10-18	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.381085+00	2025-09-08 11:34:18.80858+00
91	9	2025-10-19	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.414577+00	2025-09-08 11:34:18.837301+00
92	9	2025-10-20	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.448965+00	2025-09-08 11:34:18.865101+00
93	9	2025-10-21	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.484256+00	2025-09-08 11:34:18.892927+00
633	23	2025-09-25	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
634	23	2025-09-26	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
635	23	2025-09-27	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
636	23	2025-09-28	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
637	23	2025-09-29	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
638	23	2025-09-30	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
639	23	2025-10-01	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
640	23	2025-10-02	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
641	23	2025-10-03	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
642	23	2025-10-04	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
643	23	2025-10-05	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
644	23	2025-10-06	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
166	6	2025-09-19	09:47:00	21:00:00	254.00	1	f	t		2025-09-08 11:25:29.400212+00	2025-09-08 11:25:29.400212+00
39	9	2025-09-07	09:00:00	12:00:00	125.00	1	f	f		2025-09-07 06:25:05.863761+00	2025-09-08 11:34:17.86579+00
165	9	2025-09-19	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:25:29.368701+00	2025-09-08 11:34:17.993427+00
78	9	2025-10-06	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.021674+00	2025-09-08 11:34:18.471842+00
94	9	2025-10-22	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.518611+00	2025-09-08 11:34:18.920858+00
95	9	2025-10-23	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.555542+00	2025-09-08 11:34:18.948719+00
96	9	2025-10-24	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.589411+00	2025-09-08 11:34:18.977195+00
97	9	2025-10-25	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.61983+00	2025-09-08 11:34:19.005163+00
98	9	2025-10-26	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.648706+00	2025-09-08 11:34:19.033161+00
99	9	2025-10-27	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.677091+00	2025-09-08 11:34:19.06094+00
100	9	2025-10-28	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.705093+00	2025-09-08 11:34:19.09487+00
101	9	2025-10-29	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.733212+00	2025-09-08 11:34:19.125691+00
102	9	2025-10-30	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.761529+00	2025-09-08 11:34:19.155157+00
103	9	2025-10-31	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.789319+00	2025-09-08 11:34:19.186096+00
104	9	2025-11-01	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.817376+00	2025-09-08 11:34:19.215625+00
105	9	2025-11-02	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.845133+00	2025-09-08 11:34:19.247535+00
106	9	2025-11-03	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.87387+00	2025-09-08 11:34:19.278634+00
107	9	2025-11-04	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.903629+00	2025-09-08 11:34:19.310456+00
108	9	2025-11-05	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.931482+00	2025-09-08 11:34:19.341643+00
109	9	2025-11-06	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.958995+00	2025-09-08 11:34:19.374165+00
110	9	2025-11-07	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:54.9877+00	2025-09-08 11:34:19.408718+00
111	9	2025-11-08	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.015446+00	2025-09-08 11:34:19.443569+00
112	9	2025-11-09	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.04333+00	2025-09-08 11:34:19.478534+00
113	9	2025-11-10	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.071237+00	2025-09-08 11:34:19.51378+00
114	9	2025-11-11	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.099059+00	2025-09-08 11:34:19.547128+00
115	9	2025-11-12	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.127799+00	2025-09-08 11:34:19.577755+00
116	9	2025-11-13	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.15559+00	2025-09-08 11:34:19.609399+00
117	9	2025-11-14	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.183527+00	2025-09-08 11:34:19.63936+00
118	9	2025-11-15	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.211399+00	2025-09-08 11:34:19.671309+00
119	9	2025-11-16	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.239596+00	2025-09-08 11:34:19.702307+00
120	9	2025-11-17	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.267382+00	2025-09-08 11:34:19.732083+00
121	9	2025-11-18	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.295297+00	2025-09-08 11:34:19.76138+00
122	9	2025-11-19	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.322723+00	2025-09-08 11:34:19.789258+00
123	9	2025-11-20	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.350415+00	2025-09-08 11:34:19.81715+00
124	9	2025-11-21	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.377825+00	2025-09-08 11:34:19.845036+00
125	9	2025-11-22	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.405489+00	2025-09-08 11:34:19.872687+00
126	9	2025-11-23	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.433314+00	2025-09-08 11:34:19.90055+00
127	9	2025-11-24	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.460882+00	2025-09-08 11:34:19.928304+00
128	9	2025-11-25	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.488497+00	2025-09-08 11:34:19.956889+00
129	9	2025-11-26	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.515864+00	2025-09-08 11:34:19.984704+00
130	9	2025-11-27	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.542988+00	2025-09-08 11:34:20.012731+00
131	9	2025-11-28	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.570461+00	2025-09-08 11:34:20.040919+00
132	9	2025-11-29	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.597927+00	2025-09-08 11:34:20.068932+00
133	9	2025-11-30	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.625598+00	2025-09-08 11:34:20.097266+00
134	9	2025-12-01	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.653054+00	2025-09-08 11:34:20.12558+00
135	9	2025-12-02	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.680629+00	2025-09-08 11:34:20.154345+00
136	9	2025-12-03	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.708238+00	2025-09-08 11:34:20.183507+00
137	9	2025-12-04	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.735809+00	2025-09-08 11:34:20.212609+00
138	9	2025-12-05	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.763251+00	2025-09-08 11:34:20.240662+00
139	9	2025-12-06	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.791305+00	2025-09-08 11:34:20.271912+00
140	9	2025-12-07	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.81927+00	2025-09-08 11:34:20.300467+00
141	9	2025-12-08	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.846996+00	2025-09-08 11:34:20.328737+00
142	9	2025-12-09	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.874695+00	2025-09-08 11:34:20.35706+00
143	9	2025-12-10	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.902748+00	2025-09-08 11:34:20.385907+00
144	9	2025-12-11	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.930657+00	2025-09-08 11:34:20.414117+00
145	9	2025-12-12	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.959089+00	2025-09-08 11:34:20.442111+00
146	9	2025-12-13	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:55.987152+00	2025-09-08 11:34:20.470635+00
147	9	2025-12-14	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:56.014823+00	2025-09-08 11:34:20.499046+00
148	9	2025-12-15	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:56.042415+00	2025-09-08 11:34:20.527233+00
149	9	2025-12-16	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:56.069928+00	2025-09-08 11:34:20.555381+00
150	9	2025-12-17	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:56.097946+00	2025-09-08 11:34:20.582918+00
151	9	2025-12-18	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:56.125996+00	2025-09-08 11:34:20.611138+00
152	9	2025-12-19	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:56.154458+00	2025-09-08 11:34:20.638653+00
153	9	2025-12-20	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:56.182028+00	2025-09-08 11:34:20.666714+00
154	9	2025-12-21	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:56.210292+00	2025-09-08 11:34:20.694745+00
155	9	2025-12-22	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:56.237931+00	2025-09-08 11:34:20.722514+00
156	9	2025-12-23	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:56.265613+00	2025-09-08 11:34:20.750514+00
157	9	2025-12-24	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:56.29418+00	2025-09-08 11:34:20.778468+00
158	9	2025-12-25	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:56.322443+00	2025-09-08 11:34:20.806532+00
159	9	2025-12-26	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:56.350348+00	2025-09-08 11:34:20.834626+00
160	9	2025-12-27	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:56.378566+00	2025-09-08 11:34:20.863741+00
161	9	2025-12-28	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:56.406329+00	2025-09-08 11:34:20.893003+00
162	9	2025-12-29	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:56.434824+00	2025-09-08 11:34:20.921075+00
163	9	2025-12-30	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:56.463084+00	2025-09-08 11:34:20.949315+00
164	9	2025-12-31	09:47:00	21:00:00	254.00	1	f	f		2025-09-08 11:20:56.491504+00	2025-09-08 11:34:20.977249+00
645	23	2025-10-07	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
168	9	2025-09-21	09:00:00	12:00:00	250.00	1	f	t		2025-09-08 11:34:58.343141+00	2025-09-08 11:34:58.343141+00
169	9	2025-09-22	09:00:00	12:00:00	250.00	1	f	t		2025-09-08 11:34:58.37159+00	2025-09-08 11:34:58.37159+00
170	9	2025-09-23	09:00:00	12:00:00	250.00	1	f	t		2025-09-08 11:34:58.399708+00	2025-09-08 11:34:58.399708+00
171	9	2025-09-24	09:00:00	12:00:00	250.00	1	f	t		2025-09-08 11:34:58.427419+00	2025-09-08 11:34:58.427419+00
172	9	2025-09-25	09:00:00	12:00:00	250.00	1	f	t		2025-09-08 11:34:58.455773+00	2025-09-08 11:34:58.455773+00
173	9	2025-09-26	09:00:00	12:00:00	250.00	1	f	t		2025-09-08 11:34:58.483917+00	2025-09-08 11:34:58.483917+00
174	9	2025-09-27	09:00:00	12:00:00	250.00	1	f	t		2025-09-08 11:34:58.512161+00	2025-09-08 11:34:58.512161+00
175	9	2025-09-28	09:00:00	12:00:00	250.00	1	f	t		2025-09-08 11:34:58.540119+00	2025-09-08 11:34:58.540119+00
176	9	2025-09-29	09:00:00	12:00:00	250.00	1	f	t		2025-09-08 11:34:58.568013+00	2025-09-08 11:34:58.568013+00
177	9	2025-09-30	09:00:00	12:00:00	250.00	1	f	t		2025-09-08 11:34:58.595879+00	2025-09-08 11:34:58.595879+00
2490	2	2025-09-17	10:00:00	22:00:00	250.00	1	f	t		2025-09-17 14:31:59.978161+00	2025-09-17 14:31:59.978161+00
167	9	2025-09-20	09:01:00	12:00:00	250.00	1	f	f		2025-09-08 11:34:58.285302+00	2025-09-10 17:30:29.242738+00
180	11	2025-09-15	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-09 13:09:27.203144+00	2025-09-09 13:09:27.203144+00
646	23	2025-10-08	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
647	23	2025-10-09	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
183	11	2025-09-11	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-09 13:09:35.624612+00	2025-09-09 13:09:35.624612+00
184	11	2025-09-12	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-09 13:09:35.624612+00	2025-09-09 13:09:35.624612+00
185	11	2025-09-13	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-09 13:09:35.624612+00	2025-09-09 13:09:35.624612+00
186	11	2025-09-14	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-09 13:09:35.624612+00	2025-09-09 13:09:35.624612+00
648	23	2025-10-10	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
188	11	2025-09-09	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-09 13:11:44.080291+00	2025-09-09 13:11:44.080291+00
189	11	2025-09-10	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-09 13:11:44.080291+00	2025-09-09 13:11:44.080291+00
649	23	2025-10-11	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
650	23	2025-10-12	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
651	23	2025-10-13	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
652	23	2025-10-14	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
653	23	2025-10-15	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
195	12	2025-09-09	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-09 13:18:51.821972+00	2025-09-09 13:18:51.821972+00
196	12	2025-09-10	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-09 13:18:51.821972+00	2025-09-09 13:18:51.821972+00
197	12	2025-09-11	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-09 13:18:51.821972+00	2025-09-09 13:18:51.821972+00
198	12	2025-09-12	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-09 13:18:51.821972+00	2025-09-09 13:18:51.821972+00
199	12	2025-09-13	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-09 13:18:51.821972+00	2025-09-09 13:18:51.821972+00
200	12	2025-09-14	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-09 13:18:51.821972+00	2025-09-09 13:18:51.821972+00
201	12	2025-09-15	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-09 13:18:51.821972+00	2025-09-09 13:18:51.821972+00
202	12	2025-09-10	20:00:00	23:00:00	360.00	1	t	t	\N	2025-09-09 13:19:02.926276+00	2025-09-09 13:19:02.926276+00
203	9	2025-10-01	09:00:00	21:00:00	250.00	1	f	t		2025-09-10 12:11:39.134187+00	2025-09-10 12:11:39.134187+00
204	9	2025-10-02	09:00:00	21:00:00	250.00	1	f	t		2025-09-10 12:11:39.173249+00	2025-09-10 12:11:39.173249+00
205	9	2025-10-03	09:00:00	21:00:00	250.00	1	f	t		2025-09-10 12:11:39.204892+00	2025-09-10 12:11:39.204892+00
206	9	2025-10-04	09:00:00	21:00:00	250.00	1	f	t		2025-09-10 12:11:39.234808+00	2025-09-10 12:11:39.234808+00
207	9	2025-10-05	09:00:00	21:00:00	250.00	1	f	t		2025-09-10 12:11:39.266595+00	2025-09-10 12:11:39.266595+00
208	9	2025-10-06	09:00:00	21:00:00	250.00	1	f	t		2025-09-10 12:11:39.299071+00	2025-09-10 12:11:39.299071+00
209	9	2025-10-07	09:00:00	21:00:00	250.00	1	f	t		2025-09-10 12:11:39.331289+00	2025-09-10 12:11:39.331289+00
210	9	2025-10-08	09:00:00	21:00:00	250.00	1	f	t		2025-09-10 12:11:39.362089+00	2025-09-10 12:11:39.362089+00
211	9	2025-10-09	09:00:00	21:00:00	250.00	1	f	t		2025-09-10 12:11:39.39705+00	2025-09-10 12:11:39.39705+00
212	9	2025-10-10	09:00:00	21:00:00	250.00	1	f	t		2025-09-10 12:11:39.429057+00	2025-09-10 12:11:39.429057+00
654	23	2025-10-16	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
655	23	2025-10-17	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
656	23	2025-10-18	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
657	23	2025-10-19	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
658	23	2025-10-20	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
659	23	2025-10-21	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
660	23	2025-10-22	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
661	23	2025-10-23	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
662	23	2025-10-24	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
663	23	2025-10-25	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
664	23	2025-10-26	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
665	23	2025-10-27	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
666	23	2025-10-28	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
667	23	2025-10-29	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
668	23	2025-10-30	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
669	23	2025-10-31	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
670	23	2025-11-01	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
671	23	2025-11-02	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
672	23	2025-11-03	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
673	23	2025-11-04	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
674	23	2025-11-05	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
675	23	2025-11-06	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
676	23	2025-11-07	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
677	23	2025-11-08	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
678	23	2025-11-09	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
679	23	2025-11-10	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
680	23	2025-11-11	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
681	23	2025-11-12	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
682	23	2025-11-13	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
683	23	2025-11-14	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
684	23	2025-11-15	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
685	23	2025-11-16	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
686	23	2025-11-17	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
687	23	2025-11-18	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
688	23	2025-11-19	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
689	23	2025-11-20	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
690	23	2025-11-21	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
691	23	2025-11-22	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
692	23	2025-11-23	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
693	23	2025-11-24	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
694	23	2025-11-25	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
695	23	2025-11-26	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
696	23	2025-11-27	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
697	23	2025-11-28	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
698	23	2025-11-29	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
699	23	2025-11-30	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
700	23	2025-12-01	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
701	23	2025-12-02	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
702	23	2025-12-03	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
703	23	2025-12-04	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
704	23	2025-12-05	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
705	23	2025-12-06	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
706	23	2025-12-07	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
707	23	2025-12-08	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
708	23	2025-12-09	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
709	23	2025-12-10	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
710	23	2025-12-11	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
711	23	2025-12-12	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
712	23	2025-12-13	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
713	23	2025-12-14	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
714	23	2025-12-15	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
715	23	2025-12-16	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
716	23	2025-12-17	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
717	23	2025-12-18	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
718	23	2025-12-19	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
719	23	2025-12-20	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
720	23	2025-12-21	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
721	23	2025-12-22	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
722	23	2025-12-23	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
723	23	2025-12-24	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
724	23	2025-12-25	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
725	23	2025-12-26	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
726	23	2025-12-27	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
727	23	2025-12-28	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
728	23	2025-12-29	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
729	23	2025-12-30	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
730	23	2025-12-31	09:00:00	21:00:00	\N	1	f	t	\N	2025-09-12 08:33:34.04271+00	2025-09-12 08:33:34.04271+00
731	23	2025-09-14	15:00:00	21:00:00	200.00	2	f	t		2025-09-12 08:43:50.488228+00	2025-09-12 11:41:54.475528+00
732	9	2025-09-10	09:00:00	21:00:00	500.00	1	f	t		2025-09-12 13:09:18.387488+00	2025-09-12 13:09:18.387488+00
733	9	2025-09-12	09:00:00	21:00:00	500.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:40:33.981619+00	2025-09-12 13:40:33.981619+00
735	9	2025-09-16	09:00:00	21:00:00	500.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:40:34.062372+00	2025-09-12 13:40:34.062372+00
736	9	2025-09-17	09:00:00	21:00:00	500.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:40:34.091972+00	2025-09-12 13:40:34.091972+00
737	9	2025-09-18	09:00:00	21:00:00	500.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:40:34.121018+00	2025-09-12 13:40:34.121018+00
738	9	2025-09-19	09:00:00	21:00:00	500.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:40:34.151159+00	2025-09-12 13:40:34.151159+00
739	6	2025-09-15	09:00:00	21:00:00	150.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:43:52.207362+00	2025-09-12 13:43:52.207362+00
740	6	2025-09-17	09:00:00	21:00:00	150.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:43:52.247102+00	2025-09-12 13:43:52.247102+00
741	6	2025-09-18	09:00:00	21:00:00	150.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:43:52.280962+00	2025-09-12 13:43:52.280962+00
742	6	2025-09-19	09:00:00	09:47:00	150.00	1	f	t	Автоматически создан для заполнения пробела во времени	2025-09-12 13:43:52.315474+00	2025-09-12 13:43:52.315474+00
743	6	2025-09-22	09:00:00	21:00:00	150.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:43:52.35238+00	2025-09-12 13:43:52.35238+00
744	6	2025-09-23	09:00:00	21:00:00	150.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:43:52.389226+00	2025-09-12 13:43:52.389226+00
745	6	2025-09-24	09:00:00	21:00:00	150.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:43:52.423643+00	2025-09-12 13:43:52.423643+00
746	6	2025-09-25	09:00:00	21:00:00	150.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:43:52.458022+00	2025-09-12 13:43:52.458022+00
747	6	2025-09-26	09:00:00	21:00:00	150.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:43:52.491849+00	2025-09-12 13:43:52.491849+00
748	6	2025-09-29	09:00:00	21:00:00	150.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:43:52.528106+00	2025-09-12 13:43:52.528106+00
749	6	2025-09-30	09:00:00	21:00:00	150.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:43:52.559174+00	2025-09-12 13:43:52.559174+00
750	6	2025-10-01	09:00:00	21:00:00	150.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:43:52.588513+00	2025-09-12 13:43:52.588513+00
751	6	2025-10-02	09:00:00	21:00:00	150.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:43:52.617769+00	2025-09-12 13:43:52.617769+00
752	6	2025-10-03	09:00:00	21:00:00	150.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:43:52.647688+00	2025-09-12 13:43:52.647688+00
753	6	2025-10-06	09:00:00	21:00:00	150.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:43:52.676124+00	2025-09-12 13:43:52.676124+00
754	6	2025-10-07	09:00:00	21:00:00	150.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:43:52.706515+00	2025-09-12 13:43:52.706515+00
755	6	2025-10-08	09:00:00	21:00:00	150.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:43:52.736425+00	2025-09-12 13:43:52.736425+00
756	6	2025-10-09	09:00:00	21:00:00	150.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:43:52.765145+00	2025-09-12 13:43:52.765145+00
757	6	2025-10-10	09:00:00	21:00:00	150.00	1	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:43:52.79644+00	2025-09-12 13:43:52.79644+00
758	9	2025-09-22	12:00:00	21:00:00	500.00	1	f	t	Автоматически создан для заполнения пробела в конце дня	2025-09-12 13:44:32.110635+00	2025-09-12 13:44:32.110635+00
759	9	2025-09-23	12:00:00	21:00:00	500.00	1	f	t	Автоматически создан для заполнения пробела в конце дня	2025-09-12 13:44:32.145791+00	2025-09-12 13:44:32.145791+00
760	9	2025-09-24	12:00:00	21:00:00	500.00	1	f	t	Автоматически создан для заполнения пробела в конце дня	2025-09-12 13:44:32.178201+00	2025-09-12 13:44:32.178201+00
761	9	2025-09-25	12:00:00	21:00:00	500.00	1	f	t	Автоматически создан для заполнения пробела в конце дня	2025-09-12 13:44:32.209847+00	2025-09-12 13:44:32.209847+00
839	2	2026-04-10	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
840	2	2026-04-13	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
762	9	2025-09-26	12:00:00	21:00:00	500.00	1	f	t	Автоматически создан для заполнения пробела в конце дня	2025-09-12 13:44:32.241546+00	2025-09-12 13:44:32.241546+00
763	9	2025-09-29	12:00:00	21:00:00	500.00	1	f	t	Автоматически создан для заполнения пробела в конце дня	2025-09-12 13:44:32.274336+00	2025-09-12 13:44:32.274336+00
764	9	2025-09-30	12:00:00	21:00:00	500.00	1	f	t	Автоматически создан для заполнения пробела в конце дня	2025-09-12 13:44:32.304772+00	2025-09-12 13:44:32.304772+00
765	9	2025-09-13	09:00:00	21:00:00	150.00	1	f	t		2025-09-12 13:58:56.732572+00	2025-09-12 13:58:56.732572+00
766	12	2025-09-17	10:00:00	22:00:00	300.00	1	f	t		2025-09-13 11:42:01.60018+00	2025-09-13 11:42:01.60018+00
734	9	2025-09-15	09:00:00	21:00:00	500.00	2	f	t	Автоматически создан для заполнения пробела	2025-09-12 13:40:34.03046+00	2025-09-14 06:14:00.860734+00
767	9	2025-09-14	09:00:00	21:00:00	150.00	1	f	t		2025-09-14 06:32:53.868323+00	2025-09-14 06:32:53.868323+00
768	2	2026-01-01	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
769	2	2026-01-02	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
771	2	2026-01-06	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
772	2	2026-01-07	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
773	2	2026-01-08	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
774	2	2026-01-09	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
775	2	2026-01-12	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
776	2	2026-01-13	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
777	2	2026-01-14	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
778	2	2026-01-15	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
779	2	2026-01-16	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
780	2	2026-01-19	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
781	2	2026-01-20	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
782	2	2026-01-21	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
783	2	2026-01-22	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
784	2	2026-01-23	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
785	2	2026-01-26	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
786	2	2026-01-27	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
787	2	2026-01-28	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
788	2	2026-01-29	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
789	2	2026-01-30	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
790	2	2026-02-02	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
791	2	2026-02-03	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
792	2	2026-02-04	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
793	2	2026-02-05	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
794	2	2026-02-06	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
795	2	2026-02-09	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
796	2	2026-02-10	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
797	2	2026-02-11	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
798	2	2026-02-12	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
799	2	2026-02-13	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
800	2	2026-02-16	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
801	2	2026-02-17	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
802	2	2026-02-18	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
803	2	2026-02-19	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
804	2	2026-02-20	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
805	2	2026-02-23	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
806	2	2026-02-24	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
807	2	2026-02-25	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
808	2	2026-02-26	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
809	2	2026-02-27	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
810	2	2026-03-02	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
811	2	2026-03-03	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
812	2	2026-03-04	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
813	2	2026-03-05	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
814	2	2026-03-06	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
815	2	2026-03-09	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
816	2	2026-03-10	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
817	2	2026-03-11	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
818	2	2026-03-12	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
819	2	2026-03-13	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
820	2	2026-03-16	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
821	2	2026-03-17	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
822	2	2026-03-18	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
823	2	2026-03-19	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
824	2	2026-03-20	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
825	2	2026-03-23	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
826	2	2026-03-24	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
827	2	2026-03-25	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
828	2	2026-03-26	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
829	2	2026-03-27	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
830	2	2026-03-30	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
831	2	2026-03-31	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
832	2	2026-04-01	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
833	2	2026-04-02	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
834	2	2026-04-03	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
835	2	2026-04-06	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
836	2	2026-04-07	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
837	2	2026-04-08	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
838	2	2026-04-09	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
841	2	2026-04-14	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
842	2	2026-04-15	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
843	2	2026-04-16	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
844	2	2026-04-17	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
845	2	2026-04-20	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
846	2	2026-04-21	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
847	2	2026-04-22	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
848	2	2026-04-23	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
849	2	2026-04-24	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
850	2	2026-04-27	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
851	2	2026-04-28	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
852	2	2026-04-29	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
853	2	2026-04-30	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
854	2	2026-05-01	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
855	2	2026-05-04	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
856	2	2026-05-05	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
857	2	2026-05-06	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
858	2	2026-05-07	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
859	2	2026-05-08	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
860	2	2026-05-11	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
861	2	2026-05-12	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
862	2	2026-05-13	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
863	2	2026-05-14	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
864	2	2026-05-15	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
865	2	2026-05-18	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
866	2	2026-05-19	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
867	2	2026-05-20	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
868	2	2026-05-21	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
869	2	2026-05-22	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
870	2	2026-05-25	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
871	2	2026-05-26	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
872	2	2026-05-27	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
873	2	2026-05-28	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
874	2	2026-05-29	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
875	2	2026-06-01	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
876	2	2026-06-02	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
877	2	2026-06-03	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
878	2	2026-06-04	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
879	2	2026-06-05	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
880	2	2026-06-08	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
881	2	2026-06-09	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
882	2	2026-06-10	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
883	2	2026-06-11	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
884	2	2026-06-12	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
885	2	2026-06-15	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
886	2	2026-06-16	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
887	2	2026-06-17	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
888	2	2026-06-18	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
889	2	2026-06-19	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
890	2	2026-06-22	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
891	2	2026-06-23	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
892	2	2026-06-24	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
893	2	2026-06-25	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
894	2	2026-06-26	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
895	2	2026-06-29	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
896	2	2026-06-30	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
897	2	2026-07-01	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
898	2	2026-07-02	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
899	2	2026-07-03	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
900	2	2026-07-06	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
901	2	2026-07-07	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
902	2	2026-07-08	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
903	2	2026-07-09	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
904	2	2026-07-10	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
905	2	2026-07-13	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
906	2	2026-07-14	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
907	2	2026-07-15	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
908	2	2026-07-16	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
909	2	2026-07-17	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
910	2	2026-07-20	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
911	2	2026-07-21	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
912	2	2026-07-22	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
913	2	2026-07-23	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
914	2	2026-07-24	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
915	2	2026-07-27	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
916	2	2026-07-28	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
917	2	2026-07-29	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
918	2	2026-07-30	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
919	2	2026-07-31	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
920	2	2026-08-03	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
921	2	2026-08-04	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
922	2	2026-08-05	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
923	2	2026-08-06	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
924	2	2026-08-07	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
925	2	2026-08-10	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
926	2	2026-08-11	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
927	2	2026-08-12	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
928	2	2026-08-13	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
929	2	2026-08-14	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
930	2	2026-08-17	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
931	2	2026-08-18	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
932	2	2026-08-19	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
933	2	2026-08-20	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
934	2	2026-08-21	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
935	2	2026-08-24	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
936	2	2026-08-25	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
937	2	2026-08-26	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
938	2	2026-08-27	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
939	2	2026-08-28	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
940	2	2026-08-31	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
941	2	2026-09-01	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
942	2	2026-09-02	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
943	2	2026-09-03	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
944	2	2026-09-04	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
945	2	2026-09-07	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
946	2	2026-09-08	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
947	2	2026-09-09	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
948	2	2026-09-10	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
949	2	2026-09-11	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
950	2	2026-09-14	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
951	2	2026-09-15	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
952	2	2026-09-16	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
953	2	2026-09-17	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
954	2	2026-09-18	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
955	2	2026-09-21	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
956	2	2026-09-22	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
957	2	2026-09-23	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
958	2	2026-09-24	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
959	2	2026-09-25	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
960	2	2026-09-28	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
961	2	2026-09-29	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
962	2	2026-09-30	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
963	2	2026-10-01	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
964	2	2026-10-02	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
965	2	2026-10-05	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
966	2	2026-10-06	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
967	2	2026-10-07	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
968	2	2026-10-08	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
969	2	2026-10-09	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
970	2	2026-10-12	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
971	2	2026-10-13	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
972	2	2026-10-14	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
973	2	2026-10-15	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
974	2	2026-10-16	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
975	2	2026-10-19	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
976	2	2026-10-20	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
977	2	2026-10-21	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
978	2	2026-10-22	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
979	2	2026-10-23	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
980	2	2026-10-26	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
981	2	2026-10-27	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
982	2	2026-10-28	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
983	2	2026-10-29	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
984	2	2026-10-30	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
985	2	2026-11-02	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
986	2	2026-11-03	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
987	2	2026-11-04	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
988	2	2026-11-05	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
989	2	2026-11-06	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
990	2	2026-11-09	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
991	2	2026-11-10	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
992	2	2026-11-11	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
993	2	2026-11-12	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
994	2	2026-11-13	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
995	2	2026-11-16	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
996	2	2026-11-17	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
997	2	2026-11-18	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
998	2	2026-11-19	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
999	2	2026-11-20	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1000	2	2026-11-23	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1001	2	2026-11-24	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1002	2	2026-11-25	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1003	2	2026-11-26	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1004	2	2026-11-27	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1005	2	2026-11-30	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1006	2	2026-12-01	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1007	2	2026-12-02	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1008	2	2026-12-03	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1009	2	2026-12-04	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1010	2	2026-12-07	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1011	2	2026-12-08	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1012	2	2026-12-09	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1013	2	2026-12-10	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1014	2	2026-12-11	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1015	2	2026-12-14	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1016	2	2026-12-15	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1017	2	2026-12-16	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1018	2	2026-12-17	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1019	2	2026-12-18	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1020	2	2026-12-21	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1021	2	2026-12-22	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1022	2	2026-12-23	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1023	2	2026-12-24	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1024	2	2026-12-25	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1025	2	2026-12-28	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1026	2	2026-12-29	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1027	2	2026-12-30	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1028	2	2026-12-31	10:00:00	22:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1029	23	2026-01-01	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1030	23	2026-01-02	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1031	23	2026-01-03	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1032	23	2026-01-04	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1033	23	2026-01-05	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1034	23	2026-01-06	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1035	23	2026-01-07	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1036	23	2026-01-08	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1037	23	2026-01-09	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1038	23	2026-01-10	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1039	23	2026-01-11	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1040	23	2026-01-12	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1041	23	2026-01-13	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1042	23	2026-01-14	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1043	23	2026-01-15	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1044	23	2026-01-16	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1045	23	2026-01-17	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1046	23	2026-01-18	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1047	23	2026-01-19	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1048	23	2026-01-20	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1049	23	2026-01-21	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1050	23	2026-01-22	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1051	23	2026-01-23	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1052	23	2026-01-24	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1053	23	2026-01-25	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1054	23	2026-01-26	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1055	23	2026-01-27	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1056	23	2026-01-28	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1057	23	2026-01-29	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1058	23	2026-01-30	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1059	23	2026-01-31	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1060	23	2026-02-01	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1061	23	2026-02-02	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1062	23	2026-02-03	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1063	23	2026-02-04	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1064	23	2026-02-05	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1065	23	2026-02-06	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1066	23	2026-02-07	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1067	23	2026-02-08	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1068	23	2026-02-09	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1069	23	2026-02-10	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1070	23	2026-02-11	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1071	23	2026-02-12	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1072	23	2026-02-13	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1073	23	2026-02-14	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1074	23	2026-02-15	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1075	23	2026-02-16	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1076	23	2026-02-17	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1077	23	2026-02-18	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1078	23	2026-02-19	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1079	23	2026-02-20	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1080	23	2026-02-21	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1081	23	2026-02-22	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1082	23	2026-02-23	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1083	23	2026-02-24	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1084	23	2026-02-25	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1085	23	2026-02-26	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1086	23	2026-02-27	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1087	23	2026-02-28	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1088	23	2026-03-01	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1089	23	2026-03-02	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1090	23	2026-03-03	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1091	23	2026-03-04	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1092	23	2026-03-05	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1093	23	2026-03-06	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1094	23	2026-03-07	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1095	23	2026-03-08	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1096	23	2026-03-09	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1097	23	2026-03-10	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1098	23	2026-03-11	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1099	23	2026-03-12	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1100	23	2026-03-13	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1101	23	2026-03-14	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1102	23	2026-03-15	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1103	23	2026-03-16	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1104	23	2026-03-17	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1105	23	2026-03-18	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1106	23	2026-03-19	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1107	23	2026-03-20	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1108	23	2026-03-21	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1109	23	2026-03-22	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1110	23	2026-03-23	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1111	23	2026-03-24	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1112	23	2026-03-25	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1113	23	2026-03-26	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1114	23	2026-03-27	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1115	23	2026-03-28	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1116	23	2026-03-29	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1117	23	2026-03-30	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1118	23	2026-03-31	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1119	23	2026-04-01	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1120	23	2026-04-02	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1121	23	2026-04-03	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1122	23	2026-04-04	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1123	23	2026-04-05	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1124	23	2026-04-06	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1125	23	2026-04-07	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1126	23	2026-04-08	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1127	23	2026-04-09	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1128	23	2026-04-10	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1129	23	2026-04-11	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1130	23	2026-04-12	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1131	23	2026-04-13	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1132	23	2026-04-14	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1133	23	2026-04-15	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1134	23	2026-04-16	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1135	23	2026-04-17	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1136	23	2026-04-18	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1137	23	2026-04-19	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1138	23	2026-04-20	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1139	23	2026-04-21	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1140	23	2026-04-22	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1141	23	2026-04-23	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1142	23	2026-04-24	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1143	23	2026-04-25	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1144	23	2026-04-26	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1145	23	2026-04-27	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1146	23	2026-04-28	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1147	23	2026-04-29	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1148	23	2026-04-30	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1149	23	2026-05-01	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1150	23	2026-05-02	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1151	23	2026-05-03	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1152	23	2026-05-04	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1153	23	2026-05-05	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1154	23	2026-05-06	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1155	23	2026-05-07	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1156	23	2026-05-08	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1157	23	2026-05-09	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1158	23	2026-05-10	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1159	23	2026-05-11	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1160	23	2026-05-12	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1161	23	2026-05-13	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1162	23	2026-05-14	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1163	23	2026-05-15	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1164	23	2026-05-16	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1165	23	2026-05-17	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1166	23	2026-05-18	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1167	23	2026-05-19	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1168	23	2026-05-20	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1169	23	2026-05-21	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1170	23	2026-05-22	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1171	23	2026-05-23	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1172	23	2026-05-24	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1173	23	2026-05-25	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1174	23	2026-05-26	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1175	23	2026-05-27	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1176	23	2026-05-28	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1177	23	2026-05-29	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1178	23	2026-05-30	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1179	23	2026-05-31	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1180	23	2026-06-01	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1181	23	2026-06-02	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1182	23	2026-06-03	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1183	23	2026-06-04	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1184	23	2026-06-05	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1185	23	2026-06-06	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1186	23	2026-06-07	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1187	23	2026-06-08	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1188	23	2026-06-09	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1189	23	2026-06-10	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1190	23	2026-06-11	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1191	23	2026-06-12	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1192	23	2026-06-13	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1193	23	2026-06-14	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1194	23	2026-06-15	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1195	23	2026-06-16	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1196	23	2026-06-17	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1197	23	2026-06-18	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1198	23	2026-06-19	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1199	23	2026-06-20	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1200	23	2026-06-21	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1201	23	2026-06-22	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1202	23	2026-06-23	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1203	23	2026-06-24	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1204	23	2026-06-25	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1205	23	2026-06-26	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1206	23	2026-06-27	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1207	23	2026-06-28	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1208	23	2026-06-29	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1209	23	2026-06-30	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1210	23	2026-07-01	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1211	23	2026-07-02	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1212	23	2026-07-03	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1213	23	2026-07-04	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1214	23	2026-07-05	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1215	23	2026-07-06	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1216	23	2026-07-07	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1217	23	2026-07-08	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1218	23	2026-07-09	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1219	23	2026-07-10	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1220	23	2026-07-11	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1221	23	2026-07-12	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1222	23	2026-07-13	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1223	23	2026-07-14	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1224	23	2026-07-15	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1225	23	2026-07-16	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1226	23	2026-07-17	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1227	23	2026-07-18	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1228	23	2026-07-19	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1229	23	2026-07-20	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1230	23	2026-07-21	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1231	23	2026-07-22	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1232	23	2026-07-23	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1233	23	2026-07-24	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1234	23	2026-07-25	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1235	23	2026-07-26	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1236	23	2026-07-27	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1237	23	2026-07-28	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1238	23	2026-07-29	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1239	23	2026-07-30	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1240	23	2026-07-31	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1241	23	2026-08-01	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1242	23	2026-08-02	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1243	23	2026-08-03	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1244	23	2026-08-04	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1245	23	2026-08-05	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1246	23	2026-08-06	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1247	23	2026-08-07	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1248	23	2026-08-08	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1249	23	2026-08-09	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1250	23	2026-08-10	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1251	23	2026-08-11	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1252	23	2026-08-12	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1253	23	2026-08-13	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1254	23	2026-08-14	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1255	23	2026-08-15	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1256	23	2026-08-16	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1257	23	2026-08-17	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1258	23	2026-08-18	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1259	23	2026-08-19	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1260	23	2026-08-20	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1261	23	2026-08-21	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1262	23	2026-08-22	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1263	23	2026-08-23	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1264	23	2026-08-24	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1265	23	2026-08-25	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1266	23	2026-08-26	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1267	23	2026-08-27	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1268	23	2026-08-28	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1269	23	2026-08-29	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1270	23	2026-08-30	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1271	23	2026-08-31	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1272	23	2026-09-01	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1273	23	2026-09-02	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1274	23	2026-09-03	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1275	23	2026-09-04	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1276	23	2026-09-05	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1277	23	2026-09-06	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1278	23	2026-09-07	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1279	23	2026-09-08	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1280	23	2026-09-09	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1281	23	2026-09-10	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1282	23	2026-09-11	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1283	23	2026-09-12	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1284	23	2026-09-13	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1285	23	2026-09-14	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1286	23	2026-09-15	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1287	23	2026-09-16	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1288	23	2026-09-17	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1289	23	2026-09-18	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1290	23	2026-09-19	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1291	23	2026-09-20	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1292	23	2026-09-21	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1293	23	2026-09-22	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1294	23	2026-09-23	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1295	23	2026-09-24	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1296	23	2026-09-25	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1297	23	2026-09-26	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1298	23	2026-09-27	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1299	23	2026-09-28	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1300	23	2026-09-29	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1301	23	2026-09-30	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1302	23	2026-10-01	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1303	23	2026-10-02	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1304	23	2026-10-03	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1305	23	2026-10-04	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1306	23	2026-10-05	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1307	23	2026-10-06	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1308	23	2026-10-07	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1309	23	2026-10-08	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1310	23	2026-10-09	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1311	23	2026-10-10	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1312	23	2026-10-11	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1313	23	2026-10-12	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1314	23	2026-10-13	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1315	23	2026-10-14	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1316	23	2026-10-15	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1317	23	2026-10-16	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1318	23	2026-10-17	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1319	23	2026-10-18	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1320	23	2026-10-19	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1321	23	2026-10-20	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1322	23	2026-10-21	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1323	23	2026-10-22	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1324	23	2026-10-23	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1325	23	2026-10-24	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1326	23	2026-10-25	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1327	23	2026-10-26	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1328	23	2026-10-27	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1329	23	2026-10-28	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1330	23	2026-10-29	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1331	23	2026-10-30	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1332	23	2026-10-31	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1333	23	2026-11-01	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1334	23	2026-11-02	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1335	23	2026-11-03	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1336	23	2026-11-04	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1337	23	2026-11-05	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1338	23	2026-11-06	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1339	23	2026-11-07	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1340	23	2026-11-08	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1341	23	2026-11-09	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1342	23	2026-11-10	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1343	23	2026-11-11	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1344	23	2026-11-12	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1345	23	2026-11-13	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1346	23	2026-11-14	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1347	23	2026-11-15	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1348	23	2026-11-16	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1349	23	2026-11-17	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1350	23	2026-11-18	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1351	23	2026-11-19	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1352	23	2026-11-20	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1353	23	2026-11-21	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1354	23	2026-11-22	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1355	23	2026-11-23	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1356	23	2026-11-24	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1357	23	2026-11-25	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1358	23	2026-11-26	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1359	23	2026-11-27	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1360	23	2026-11-28	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1361	23	2026-11-29	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1362	23	2026-11-30	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1363	23	2026-12-01	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1364	23	2026-12-02	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1365	23	2026-12-03	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1366	23	2026-12-04	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1367	23	2026-12-05	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1368	23	2026-12-06	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1369	23	2026-12-07	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1370	23	2026-12-08	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1371	23	2026-12-09	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1372	23	2026-12-10	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1373	23	2026-12-11	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1374	23	2026-12-12	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1375	23	2026-12-13	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1376	23	2026-12-14	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1377	23	2026-12-15	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1378	23	2026-12-16	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1379	23	2026-12-17	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1380	23	2026-12-18	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1381	23	2026-12-19	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1382	23	2026-12-20	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1383	23	2026-12-21	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1384	23	2026-12-22	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1385	23	2026-12-23	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1386	23	2026-12-24	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1387	23	2026-12-25	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1388	23	2026-12-26	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1389	23	2026-12-27	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1390	23	2026-12-28	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1391	23	2026-12-29	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1392	23	2026-12-30	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1393	23	2026-12-31	09:00:00	21:00:00	200.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1394	9	2026-01-01	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1395	9	2026-01-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1396	9	2026-01-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1397	9	2026-01-05	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1398	9	2026-01-06	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1399	9	2026-01-07	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1400	9	2026-01-08	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1401	9	2026-01-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1402	9	2026-01-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1403	9	2026-01-12	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1404	9	2026-01-13	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1405	9	2026-01-14	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1406	9	2026-01-15	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1407	9	2026-01-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1408	9	2026-01-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1409	9	2026-01-19	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1410	9	2026-01-20	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1411	9	2026-01-21	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1412	9	2026-01-22	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1413	9	2026-01-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1414	9	2026-01-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1415	9	2026-01-26	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1416	9	2026-01-27	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1417	9	2026-01-28	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1418	9	2026-01-29	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1419	9	2026-01-30	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1420	9	2026-01-31	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1421	9	2026-02-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1422	9	2026-02-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1423	9	2026-02-04	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1424	9	2026-02-05	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1425	9	2026-02-06	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1426	9	2026-02-07	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1427	9	2026-02-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1428	9	2026-02-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1429	9	2026-02-11	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1430	9	2026-02-12	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1431	9	2026-02-13	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1432	9	2026-02-14	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1433	9	2026-02-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1434	9	2026-02-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1435	9	2026-02-18	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1436	9	2026-02-19	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1437	9	2026-02-20	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1438	9	2026-02-21	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1439	9	2026-02-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1440	9	2026-02-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1441	9	2026-02-25	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1442	9	2026-02-26	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1443	9	2026-02-27	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1444	9	2026-02-28	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1445	9	2026-03-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1446	9	2026-03-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1447	9	2026-03-04	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1448	9	2026-03-05	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1449	9	2026-03-06	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1450	9	2026-03-07	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1451	9	2026-03-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1452	9	2026-03-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1453	9	2026-03-11	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1454	9	2026-03-12	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1455	9	2026-03-13	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1456	9	2026-03-14	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1457	9	2026-03-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1458	9	2026-03-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1459	9	2026-03-18	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1460	9	2026-03-19	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1461	9	2026-03-20	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1462	9	2026-03-21	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1463	9	2026-03-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1464	9	2026-03-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1465	9	2026-03-25	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1466	9	2026-03-26	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1467	9	2026-03-27	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1468	9	2026-03-28	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1469	9	2026-03-30	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1470	9	2026-03-31	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1471	9	2026-04-01	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1472	9	2026-04-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1473	9	2026-04-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1474	9	2026-04-04	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1475	9	2026-04-06	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1476	9	2026-04-07	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1477	9	2026-04-08	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1478	9	2026-04-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1479	9	2026-04-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1480	9	2026-04-11	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1481	9	2026-04-13	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1482	9	2026-04-14	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1483	9	2026-04-15	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1484	9	2026-04-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1485	9	2026-04-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1486	9	2026-04-18	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1487	9	2026-04-20	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1488	9	2026-04-21	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1489	9	2026-04-22	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1490	9	2026-04-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1491	9	2026-04-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1492	9	2026-04-25	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1493	9	2026-04-27	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1494	9	2026-04-28	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1495	9	2026-04-29	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1496	9	2026-04-30	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1497	9	2026-05-01	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1498	9	2026-05-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1499	9	2026-05-04	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1500	9	2026-05-05	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1501	9	2026-05-06	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1502	9	2026-05-07	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1503	9	2026-05-08	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1504	9	2026-05-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1505	9	2026-05-11	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1506	9	2026-05-12	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1507	9	2026-05-13	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1508	9	2026-05-14	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1509	9	2026-05-15	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1510	9	2026-05-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1511	9	2026-05-18	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1512	9	2026-05-19	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1513	9	2026-05-20	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1514	9	2026-05-21	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1515	9	2026-05-22	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1516	9	2026-05-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1517	9	2026-05-25	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1518	9	2026-05-26	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1519	9	2026-05-27	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1520	9	2026-05-28	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1521	9	2026-05-29	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1522	9	2026-05-30	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1523	9	2026-06-01	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1524	9	2026-06-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1525	9	2026-06-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1526	9	2026-06-04	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1527	9	2026-06-05	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1528	9	2026-06-06	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1529	9	2026-06-08	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1530	9	2026-06-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1531	9	2026-06-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1532	9	2026-06-11	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1533	9	2026-06-12	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1534	9	2026-06-13	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1535	9	2026-06-15	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1536	9	2026-06-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1537	9	2026-06-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1538	9	2026-06-18	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1539	9	2026-06-19	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1540	9	2026-06-20	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1541	9	2026-06-22	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1542	9	2026-06-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1543	9	2026-06-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1544	9	2026-06-25	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1545	9	2026-06-26	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1546	9	2026-06-27	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1547	9	2026-06-29	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1548	9	2026-06-30	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1549	9	2026-07-01	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1550	9	2026-07-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1551	9	2026-07-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1552	9	2026-07-04	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1553	9	2026-07-06	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1554	9	2026-07-07	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1555	9	2026-07-08	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1556	9	2026-07-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1557	9	2026-07-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1558	9	2026-07-11	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1559	9	2026-07-13	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1560	9	2026-07-14	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1561	9	2026-07-15	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1562	9	2026-07-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1563	9	2026-07-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1564	9	2026-07-18	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1565	9	2026-07-20	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1566	9	2026-07-21	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1567	9	2026-07-22	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1568	9	2026-07-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1569	9	2026-07-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1570	9	2026-07-25	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1571	9	2026-07-27	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1572	9	2026-07-28	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1573	9	2026-07-29	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1574	9	2026-07-30	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1575	9	2026-07-31	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1576	9	2026-08-01	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1577	9	2026-08-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1578	9	2026-08-04	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1579	9	2026-08-05	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1580	9	2026-08-06	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1581	9	2026-08-07	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1582	9	2026-08-08	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1583	9	2026-08-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1584	9	2026-08-11	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1585	9	2026-08-12	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1586	9	2026-08-13	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1587	9	2026-08-14	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1588	9	2026-08-15	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1589	9	2026-08-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1590	9	2026-08-18	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1591	9	2026-08-19	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1592	9	2026-08-20	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1593	9	2026-08-21	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1594	9	2026-08-22	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1595	9	2026-08-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1596	9	2026-08-25	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1597	9	2026-08-26	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1598	9	2026-08-27	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1599	9	2026-08-28	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1600	9	2026-08-29	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1601	9	2026-08-31	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1602	9	2026-09-01	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1603	9	2026-09-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1604	9	2026-09-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1605	9	2026-09-04	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1606	9	2026-09-05	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1607	9	2026-09-07	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1608	9	2026-09-08	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1609	9	2026-09-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1610	9	2026-09-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1611	9	2026-09-11	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1612	9	2026-09-12	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1613	9	2026-09-14	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1614	9	2026-09-15	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1615	9	2026-09-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1616	9	2026-09-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1617	9	2026-09-18	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1618	9	2026-09-19	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1619	9	2026-09-21	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1620	9	2026-09-22	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1621	9	2026-09-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1622	9	2026-09-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1623	9	2026-09-25	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1624	9	2026-09-26	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1625	9	2026-09-28	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1626	9	2026-09-29	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1627	9	2026-09-30	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1628	9	2026-10-01	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1629	9	2026-10-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1630	9	2026-10-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1631	9	2026-10-05	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1632	9	2026-10-06	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1633	9	2026-10-07	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1634	9	2026-10-08	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1635	9	2026-10-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1636	9	2026-10-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1637	9	2026-10-12	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1638	9	2026-10-13	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1639	9	2026-10-14	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1640	9	2026-10-15	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1641	9	2026-10-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1642	9	2026-10-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1643	9	2026-10-19	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1644	9	2026-10-20	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1645	9	2026-10-21	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1646	9	2026-10-22	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1647	9	2026-10-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1648	9	2026-10-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1649	9	2026-10-26	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1650	9	2026-10-27	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1651	9	2026-10-28	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1652	9	2026-10-29	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1653	9	2026-10-30	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1654	9	2026-10-31	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1655	9	2026-11-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1656	9	2026-11-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1657	9	2026-11-04	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1658	9	2026-11-05	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1659	9	2026-11-06	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1660	9	2026-11-07	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1661	9	2026-11-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1662	9	2026-11-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1663	9	2026-11-11	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1664	9	2026-11-12	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1665	9	2026-11-13	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1666	9	2026-11-14	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1667	9	2026-11-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1668	9	2026-11-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1669	9	2026-11-18	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1670	9	2026-11-19	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1671	9	2026-11-20	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1672	9	2026-11-21	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1673	9	2026-11-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1674	9	2026-11-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1675	9	2026-11-25	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1676	9	2026-11-26	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1677	9	2026-11-27	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1678	9	2026-11-28	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1679	9	2026-11-30	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1680	9	2026-12-01	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1681	9	2026-12-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1682	9	2026-12-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1683	9	2026-12-04	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1684	9	2026-12-05	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1685	9	2026-12-07	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1686	9	2026-12-08	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1687	9	2026-12-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1688	9	2026-12-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1689	9	2026-12-11	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1690	9	2026-12-12	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1691	9	2026-12-14	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1692	9	2026-12-15	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1693	9	2026-12-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1694	9	2026-12-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1695	9	2026-12-18	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1696	9	2026-12-19	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1697	9	2026-12-21	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1698	9	2026-12-22	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1699	9	2026-12-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1700	9	2026-12-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1701	9	2026-12-25	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1702	9	2026-12-26	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1703	9	2026-12-28	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1704	9	2026-12-29	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1705	9	2026-12-30	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1706	9	2026-12-31	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1707	6	2026-01-01	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1708	6	2026-01-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1709	6	2026-01-05	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1710	6	2026-01-06	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1711	6	2026-01-07	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1712	6	2026-01-08	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1713	6	2026-01-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1714	6	2026-01-12	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1715	6	2026-01-13	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1716	6	2026-01-14	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1717	6	2026-01-15	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1718	6	2026-01-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1719	6	2026-01-19	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1720	6	2026-01-20	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1721	6	2026-01-21	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1722	6	2026-01-22	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1723	6	2026-01-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1724	6	2026-01-26	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1725	6	2026-01-27	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1726	6	2026-01-28	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1727	6	2026-01-29	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1728	6	2026-01-30	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1729	6	2026-02-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1730	6	2026-02-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1731	6	2026-02-04	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1732	6	2026-02-05	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1733	6	2026-02-06	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1734	6	2026-02-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1735	6	2026-02-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1736	6	2026-02-11	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1737	6	2026-02-12	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1738	6	2026-02-13	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1739	6	2026-02-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1740	6	2026-02-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1741	6	2026-02-18	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1742	6	2026-02-19	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1743	6	2026-02-20	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1744	6	2026-02-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1745	6	2026-02-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1746	6	2026-02-25	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1747	6	2026-02-26	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1748	6	2026-02-27	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1749	6	2026-03-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1750	6	2026-03-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1751	6	2026-03-04	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1752	6	2026-03-05	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1753	6	2026-03-06	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1754	6	2026-03-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1755	6	2026-03-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1756	6	2026-03-11	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1757	6	2026-03-12	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1758	6	2026-03-13	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1759	6	2026-03-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1760	6	2026-03-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1761	6	2026-03-18	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1762	6	2026-03-19	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1763	6	2026-03-20	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1764	6	2026-03-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1765	6	2026-03-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1766	6	2026-03-25	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1767	6	2026-03-26	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1768	6	2026-03-27	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1769	6	2026-03-30	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1770	6	2026-03-31	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1771	6	2026-04-01	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1772	6	2026-04-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1773	6	2026-04-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1774	6	2026-04-06	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1775	6	2026-04-07	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1776	6	2026-04-08	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1777	6	2026-04-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1778	6	2026-04-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1779	6	2026-04-13	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1780	6	2026-04-14	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1781	6	2026-04-15	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1782	6	2026-04-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1783	6	2026-04-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1784	6	2026-04-20	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1785	6	2026-04-21	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1786	6	2026-04-22	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1787	6	2026-04-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1788	6	2026-04-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1789	6	2026-04-27	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1790	6	2026-04-28	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1791	6	2026-04-29	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1792	6	2026-04-30	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1793	6	2026-05-01	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1794	6	2026-05-04	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1795	6	2026-05-05	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1796	6	2026-05-06	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1797	6	2026-05-07	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1798	6	2026-05-08	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1799	6	2026-05-11	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1800	6	2026-05-12	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1801	6	2026-05-13	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1802	6	2026-05-14	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1803	6	2026-05-15	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1804	6	2026-05-18	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1805	6	2026-05-19	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1806	6	2026-05-20	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1807	6	2026-05-21	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1808	6	2026-05-22	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1809	6	2026-05-25	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1810	6	2026-05-26	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1811	6	2026-05-27	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1812	6	2026-05-28	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1813	6	2026-05-29	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1814	6	2026-06-01	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1815	6	2026-06-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1816	6	2026-06-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1817	6	2026-06-04	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1818	6	2026-06-05	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1819	6	2026-06-08	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1820	6	2026-06-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1821	6	2026-06-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1822	6	2026-06-11	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1823	6	2026-06-12	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1824	6	2026-06-15	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1825	6	2026-06-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1826	6	2026-06-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1827	6	2026-06-18	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1828	6	2026-06-19	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1829	6	2026-06-22	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1830	6	2026-06-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1831	6	2026-06-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1832	6	2026-06-25	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1833	6	2026-06-26	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1834	6	2026-06-29	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1835	6	2026-06-30	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1836	6	2026-07-01	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1837	6	2026-07-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1838	6	2026-07-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1839	6	2026-07-06	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1840	6	2026-07-07	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1841	6	2026-07-08	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1842	6	2026-07-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1843	6	2026-07-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1844	6	2026-07-13	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1845	6	2026-07-14	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1846	6	2026-07-15	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1847	6	2026-07-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1848	6	2026-07-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1849	6	2026-07-20	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1850	6	2026-07-21	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1851	6	2026-07-22	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1852	6	2026-07-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1853	6	2026-07-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1854	6	2026-07-27	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1855	6	2026-07-28	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1856	6	2026-07-29	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1857	6	2026-07-30	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1858	6	2026-07-31	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1859	6	2026-08-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1860	6	2026-08-04	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1861	6	2026-08-05	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1862	6	2026-08-06	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1863	6	2026-08-07	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1864	6	2026-08-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1865	6	2026-08-11	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1866	6	2026-08-12	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1867	6	2026-08-13	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1868	6	2026-08-14	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1869	6	2026-08-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1870	6	2026-08-18	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1871	6	2026-08-19	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1872	6	2026-08-20	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1873	6	2026-08-21	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1874	6	2026-08-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1875	6	2026-08-25	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1876	6	2026-08-26	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1877	6	2026-08-27	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1878	6	2026-08-28	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1879	6	2026-08-31	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1880	6	2026-09-01	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1881	6	2026-09-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1882	6	2026-09-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1883	6	2026-09-04	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1884	6	2026-09-07	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1885	6	2026-09-08	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1886	6	2026-09-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1887	6	2026-09-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1888	6	2026-09-11	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1889	6	2026-09-14	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1890	6	2026-09-15	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1891	6	2026-09-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1892	6	2026-09-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1893	6	2026-09-18	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1894	6	2026-09-21	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1895	6	2026-09-22	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1896	6	2026-09-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1897	6	2026-09-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1898	6	2026-09-25	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1899	6	2026-09-28	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1900	6	2026-09-29	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1901	6	2026-09-30	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1902	6	2026-10-01	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1903	6	2026-10-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1904	6	2026-10-05	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1905	6	2026-10-06	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1906	6	2026-10-07	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1907	6	2026-10-08	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1908	6	2026-10-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1909	6	2026-10-12	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1910	6	2026-10-13	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1911	6	2026-10-14	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1912	6	2026-10-15	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1913	6	2026-10-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1914	6	2026-10-19	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1915	6	2026-10-20	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1916	6	2026-10-21	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1917	6	2026-10-22	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1918	6	2026-10-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1919	6	2026-10-26	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1920	6	2026-10-27	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1921	6	2026-10-28	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1922	6	2026-10-29	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1923	6	2026-10-30	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1924	6	2026-11-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1925	6	2026-11-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1926	6	2026-11-04	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1927	6	2026-11-05	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1928	6	2026-11-06	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1929	6	2026-11-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1930	6	2026-11-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1931	6	2026-11-11	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1932	6	2026-11-12	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1933	6	2026-11-13	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1934	6	2026-11-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1935	6	2026-11-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1936	6	2026-11-18	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1937	6	2026-11-19	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1938	6	2026-11-20	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1939	6	2026-11-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1940	6	2026-11-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1941	6	2026-11-25	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1942	6	2026-11-26	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1943	6	2026-11-27	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1944	6	2026-11-30	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1945	6	2026-12-01	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1946	6	2026-12-02	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1947	6	2026-12-03	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1948	6	2026-12-04	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1949	6	2026-12-07	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1950	6	2026-12-08	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1951	6	2026-12-09	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1952	6	2026-12-10	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1953	6	2026-12-11	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1954	6	2026-12-14	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1955	6	2026-12-15	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1956	6	2026-12-16	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1957	6	2026-12-17	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1958	6	2026-12-18	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1959	6	2026-12-21	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1960	6	2026-12-22	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1961	6	2026-12-23	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1962	6	2026-12-24	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1963	6	2026-12-25	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1964	6	2026-12-28	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1965	6	2026-12-29	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1966	6	2026-12-30	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1967	6	2026-12-31	09:00:00	21:00:00	150.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1968	11	2026-01-01	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1969	11	2026-01-02	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1970	11	2026-01-05	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1971	11	2026-01-06	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1972	11	2026-01-07	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1973	11	2026-01-08	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1974	11	2026-01-09	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1975	11	2026-01-12	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1976	11	2026-01-13	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1977	11	2026-01-14	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1978	11	2026-01-15	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1979	11	2026-01-16	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1980	11	2026-01-19	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1981	11	2026-01-20	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1982	11	2026-01-21	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1983	11	2026-01-22	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1984	11	2026-01-23	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1985	11	2026-01-26	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1986	11	2026-01-27	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1987	11	2026-01-28	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1988	11	2026-01-29	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1989	11	2026-01-30	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1990	11	2026-02-02	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1991	11	2026-02-03	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1992	11	2026-02-04	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1993	11	2026-02-05	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1994	11	2026-02-06	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1995	11	2026-02-09	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1996	11	2026-02-10	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1997	11	2026-02-11	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1998	11	2026-02-12	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
1999	11	2026-02-13	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2000	11	2026-02-16	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2001	11	2026-02-17	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2002	11	2026-02-18	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2003	11	2026-02-19	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2004	11	2026-02-20	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2005	11	2026-02-23	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2006	11	2026-02-24	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2007	11	2026-02-25	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2008	11	2026-02-26	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2009	11	2026-02-27	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2010	11	2026-03-02	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2011	11	2026-03-03	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2012	11	2026-03-04	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2013	11	2026-03-05	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2014	11	2026-03-06	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2015	11	2026-03-09	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2016	11	2026-03-10	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2017	11	2026-03-11	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2018	11	2026-03-12	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2019	11	2026-03-13	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2020	11	2026-03-16	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2021	11	2026-03-17	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2022	11	2026-03-18	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2023	11	2026-03-19	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2024	11	2026-03-20	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2025	11	2026-03-23	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2026	11	2026-03-24	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2027	11	2026-03-25	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2028	11	2026-03-26	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2029	11	2026-03-27	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2030	11	2026-03-30	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2031	11	2026-03-31	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2032	11	2026-04-01	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2033	11	2026-04-02	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2034	11	2026-04-03	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2035	11	2026-04-06	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2036	11	2026-04-07	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2037	11	2026-04-08	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2038	11	2026-04-09	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2039	11	2026-04-10	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2040	11	2026-04-13	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2041	11	2026-04-14	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2042	11	2026-04-15	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2043	11	2026-04-16	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2044	11	2026-04-17	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2045	11	2026-04-20	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2046	11	2026-04-21	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2047	11	2026-04-22	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2048	11	2026-04-23	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2049	11	2026-04-24	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2050	11	2026-04-27	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2051	11	2026-04-28	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2052	11	2026-04-29	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2053	11	2026-04-30	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2054	11	2026-05-01	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2055	11	2026-05-04	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2056	11	2026-05-05	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2057	11	2026-05-06	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2058	11	2026-05-07	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2059	11	2026-05-08	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2060	11	2026-05-11	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2061	11	2026-05-12	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2062	11	2026-05-13	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2063	11	2026-05-14	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2064	11	2026-05-15	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2065	11	2026-05-18	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2066	11	2026-05-19	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2067	11	2026-05-20	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2068	11	2026-05-21	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2069	11	2026-05-22	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2070	11	2026-05-25	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2071	11	2026-05-26	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2072	11	2026-05-27	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2073	11	2026-05-28	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2074	11	2026-05-29	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2075	11	2026-06-01	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2076	11	2026-06-02	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2077	11	2026-06-03	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2078	11	2026-06-04	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2079	11	2026-06-05	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2080	11	2026-06-08	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2081	11	2026-06-09	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2082	11	2026-06-10	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2083	11	2026-06-11	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2084	11	2026-06-12	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2085	11	2026-06-15	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2086	11	2026-06-16	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2087	11	2026-06-17	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2088	11	2026-06-18	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2089	11	2026-06-19	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2090	11	2026-06-22	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2091	11	2026-06-23	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2092	11	2026-06-24	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2093	11	2026-06-25	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2094	11	2026-06-26	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2095	11	2026-06-29	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2096	11	2026-06-30	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2097	11	2026-07-01	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2098	11	2026-07-02	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2099	11	2026-07-03	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2100	11	2026-07-06	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2101	11	2026-07-07	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2102	11	2026-07-08	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2103	11	2026-07-09	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2104	11	2026-07-10	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2105	11	2026-07-13	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2106	11	2026-07-14	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2107	11	2026-07-15	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2108	11	2026-07-16	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2109	11	2026-07-17	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2110	11	2026-07-20	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2111	11	2026-07-21	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2112	11	2026-07-22	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2113	11	2026-07-23	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2114	11	2026-07-24	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2115	11	2026-07-27	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2116	11	2026-07-28	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2117	11	2026-07-29	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2118	11	2026-07-30	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2119	11	2026-07-31	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2120	11	2026-08-03	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2121	11	2026-08-04	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2122	11	2026-08-05	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2123	11	2026-08-06	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2124	11	2026-08-07	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2125	11	2026-08-10	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2126	11	2026-08-11	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2127	11	2026-08-12	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2128	11	2026-08-13	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2129	11	2026-08-14	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2130	11	2026-08-17	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2131	11	2026-08-18	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2132	11	2026-08-19	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2133	11	2026-08-20	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2134	11	2026-08-21	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2135	11	2026-08-24	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2136	11	2026-08-25	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2137	11	2026-08-26	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2138	11	2026-08-27	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2139	11	2026-08-28	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2140	11	2026-08-31	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2141	11	2026-09-01	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2142	11	2026-09-02	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2143	11	2026-09-03	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2144	11	2026-09-04	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2145	11	2026-09-07	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2146	11	2026-09-08	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2147	11	2026-09-09	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2148	11	2026-09-10	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2149	11	2026-09-11	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2150	11	2026-09-14	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2151	11	2026-09-15	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2152	11	2026-09-16	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2153	11	2026-09-17	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2154	11	2026-09-18	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2155	11	2026-09-21	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2156	11	2026-09-22	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2157	11	2026-09-23	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2158	11	2026-09-24	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2159	11	2026-09-25	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2160	11	2026-09-28	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2161	11	2026-09-29	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2162	11	2026-09-30	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2163	11	2026-10-01	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2164	11	2026-10-02	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2165	11	2026-10-05	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2166	11	2026-10-06	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2167	11	2026-10-07	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2168	11	2026-10-08	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2169	11	2026-10-09	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2170	11	2026-10-12	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2171	11	2026-10-13	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2172	11	2026-10-14	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2173	11	2026-10-15	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2174	11	2026-10-16	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2175	11	2026-10-19	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2176	11	2026-10-20	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2177	11	2026-10-21	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2178	11	2026-10-22	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2179	11	2026-10-23	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2180	11	2026-10-26	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2181	11	2026-10-27	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2182	11	2026-10-28	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2183	11	2026-10-29	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2184	11	2026-10-30	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2185	11	2026-11-02	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2186	11	2026-11-03	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2187	11	2026-11-04	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2188	11	2026-11-05	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2189	11	2026-11-06	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2190	11	2026-11-09	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2191	11	2026-11-10	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2192	11	2026-11-11	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2193	11	2026-11-12	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2194	11	2026-11-13	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2195	11	2026-11-16	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2196	11	2026-11-17	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2197	11	2026-11-18	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2198	11	2026-11-19	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2199	11	2026-11-20	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2200	11	2026-11-23	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2201	11	2026-11-24	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2202	11	2026-11-25	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2203	11	2026-11-26	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2204	11	2026-11-27	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2205	11	2026-11-30	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2206	11	2026-12-01	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2207	11	2026-12-02	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2208	11	2026-12-03	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2209	11	2026-12-04	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2210	11	2026-12-07	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2211	11	2026-12-08	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2212	11	2026-12-09	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2213	11	2026-12-10	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2214	11	2026-12-11	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2215	11	2026-12-14	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2216	11	2026-12-15	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2217	11	2026-12-16	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2218	11	2026-12-17	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2219	11	2026-12-18	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2220	11	2026-12-21	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2221	11	2026-12-22	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2222	11	2026-12-23	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2223	11	2026-12-24	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2224	11	2026-12-25	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2225	11	2026-12-28	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2226	11	2026-12-29	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2227	11	2026-12-30	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2228	11	2026-12-31	09:00:00	21:00:00	250.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2229	12	2026-01-01	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2230	12	2026-01-02	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2231	12	2026-01-05	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2232	12	2026-01-06	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2233	12	2026-01-07	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2234	12	2026-01-08	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2235	12	2026-01-09	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2236	12	2026-01-12	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2237	12	2026-01-13	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2238	12	2026-01-14	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2239	12	2026-01-15	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2240	12	2026-01-16	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2241	12	2026-01-19	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2242	12	2026-01-20	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2243	12	2026-01-21	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2244	12	2026-01-22	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2245	12	2026-01-23	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2246	12	2026-01-26	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2247	12	2026-01-27	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2248	12	2026-01-28	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2249	12	2026-01-29	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2250	12	2026-01-30	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2251	12	2026-02-02	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2252	12	2026-02-03	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2253	12	2026-02-04	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2254	12	2026-02-05	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2255	12	2026-02-06	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2256	12	2026-02-09	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2257	12	2026-02-10	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2258	12	2026-02-11	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2259	12	2026-02-12	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2260	12	2026-02-13	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2261	12	2026-02-16	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2262	12	2026-02-17	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2263	12	2026-02-18	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2264	12	2026-02-19	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2265	12	2026-02-20	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2266	12	2026-02-23	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2267	12	2026-02-24	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2268	12	2026-02-25	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2269	12	2026-02-26	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2270	12	2026-02-27	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2271	12	2026-03-02	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2272	12	2026-03-03	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2273	12	2026-03-04	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2274	12	2026-03-05	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2275	12	2026-03-06	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2276	12	2026-03-09	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2277	12	2026-03-10	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2278	12	2026-03-11	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2279	12	2026-03-12	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2280	12	2026-03-13	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2281	12	2026-03-16	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2282	12	2026-03-17	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2283	12	2026-03-18	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2284	12	2026-03-19	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2285	12	2026-03-20	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2286	12	2026-03-23	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2287	12	2026-03-24	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2288	12	2026-03-25	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2289	12	2026-03-26	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2290	12	2026-03-27	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2291	12	2026-03-30	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2292	12	2026-03-31	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2293	12	2026-04-01	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2294	12	2026-04-02	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2295	12	2026-04-03	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2296	12	2026-04-06	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2297	12	2026-04-07	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2298	12	2026-04-08	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2299	12	2026-04-09	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2300	12	2026-04-10	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2301	12	2026-04-13	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2302	12	2026-04-14	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2303	12	2026-04-15	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2304	12	2026-04-16	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2305	12	2026-04-17	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2306	12	2026-04-20	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2307	12	2026-04-21	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2308	12	2026-04-22	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2309	12	2026-04-23	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2310	12	2026-04-24	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2311	12	2026-04-27	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2312	12	2026-04-28	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2313	12	2026-04-29	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2314	12	2026-04-30	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2315	12	2026-05-01	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2316	12	2026-05-04	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2317	12	2026-05-05	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2318	12	2026-05-06	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2319	12	2026-05-07	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2320	12	2026-05-08	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2321	12	2026-05-11	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2322	12	2026-05-12	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2323	12	2026-05-13	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2324	12	2026-05-14	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2325	12	2026-05-15	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2326	12	2026-05-18	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2327	12	2026-05-19	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2328	12	2026-05-20	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2329	12	2026-05-21	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2330	12	2026-05-22	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2331	12	2026-05-25	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2332	12	2026-05-26	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2333	12	2026-05-27	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2334	12	2026-05-28	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2335	12	2026-05-29	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2336	12	2026-06-01	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2337	12	2026-06-02	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2338	12	2026-06-03	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2339	12	2026-06-04	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2340	12	2026-06-05	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2341	12	2026-06-08	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2342	12	2026-06-09	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2343	12	2026-06-10	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2344	12	2026-06-11	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2345	12	2026-06-12	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2346	12	2026-06-15	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2347	12	2026-06-16	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2348	12	2026-06-17	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2349	12	2026-06-18	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2350	12	2026-06-19	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2351	12	2026-06-22	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2352	12	2026-06-23	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2353	12	2026-06-24	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2354	12	2026-06-25	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2355	12	2026-06-26	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2356	12	2026-06-29	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2357	12	2026-06-30	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2358	12	2026-07-01	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2359	12	2026-07-02	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2360	12	2026-07-03	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2361	12	2026-07-06	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2362	12	2026-07-07	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2363	12	2026-07-08	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2364	12	2026-07-09	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2365	12	2026-07-10	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2366	12	2026-07-13	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2367	12	2026-07-14	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2368	12	2026-07-15	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2369	12	2026-07-16	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2370	12	2026-07-17	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2371	12	2026-07-20	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2372	12	2026-07-21	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2373	12	2026-07-22	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2374	12	2026-07-23	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2375	12	2026-07-24	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2376	12	2026-07-27	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2377	12	2026-07-28	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2378	12	2026-07-29	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2379	12	2026-07-30	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2380	12	2026-07-31	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2381	12	2026-08-03	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2382	12	2026-08-04	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2383	12	2026-08-05	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2384	12	2026-08-06	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2385	12	2026-08-07	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2386	12	2026-08-10	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2387	12	2026-08-11	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2388	12	2026-08-12	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2389	12	2026-08-13	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2390	12	2026-08-14	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2391	12	2026-08-17	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2392	12	2026-08-18	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2393	12	2026-08-19	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2394	12	2026-08-20	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2395	12	2026-08-21	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2396	12	2026-08-24	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2397	12	2026-08-25	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2398	12	2026-08-26	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2399	12	2026-08-27	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2400	12	2026-08-28	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2401	12	2026-08-31	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2402	12	2026-09-01	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2403	12	2026-09-02	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2404	12	2026-09-03	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2405	12	2026-09-04	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2406	12	2026-09-07	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2407	12	2026-09-08	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2408	12	2026-09-09	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2409	12	2026-09-10	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2410	12	2026-09-11	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2411	12	2026-09-14	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2412	12	2026-09-15	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2413	12	2026-09-16	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2414	12	2026-09-17	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2415	12	2026-09-18	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2416	12	2026-09-21	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2417	12	2026-09-22	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2418	12	2026-09-23	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2419	12	2026-09-24	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2420	12	2026-09-25	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2421	12	2026-09-28	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2422	12	2026-09-29	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2423	12	2026-09-30	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2424	12	2026-10-01	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2425	12	2026-10-02	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2426	12	2026-10-05	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2427	12	2026-10-06	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2428	12	2026-10-07	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2429	12	2026-10-08	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2430	12	2026-10-09	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2431	12	2026-10-12	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2432	12	2026-10-13	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2433	12	2026-10-14	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2434	12	2026-10-15	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2435	12	2026-10-16	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2436	12	2026-10-19	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2437	12	2026-10-20	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2438	12	2026-10-21	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2439	12	2026-10-22	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2440	12	2026-10-23	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2441	12	2026-10-26	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2442	12	2026-10-27	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2443	12	2026-10-28	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2444	12	2026-10-29	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2445	12	2026-10-30	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2446	12	2026-11-02	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2447	12	2026-11-03	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2448	12	2026-11-04	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2449	12	2026-11-05	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2450	12	2026-11-06	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2451	12	2026-11-09	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2452	12	2026-11-10	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2453	12	2026-11-11	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2454	12	2026-11-12	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2455	12	2026-11-13	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2456	12	2026-11-16	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2457	12	2026-11-17	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2458	12	2026-11-18	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2459	12	2026-11-19	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2460	12	2026-11-20	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2461	12	2026-11-23	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2462	12	2026-11-24	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2463	12	2026-11-25	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2464	12	2026-11-26	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2465	12	2026-11-27	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2466	12	2026-11-30	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2467	12	2026-12-01	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2468	12	2026-12-02	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2469	12	2026-12-03	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2470	12	2026-12-04	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2471	12	2026-12-07	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2472	12	2026-12-08	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2473	12	2026-12-09	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2474	12	2026-12-10	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2475	12	2026-12-11	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2476	12	2026-12-14	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2477	12	2026-12-15	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2478	12	2026-12-16	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2479	12	2026-12-17	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2480	12	2026-12-18	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2481	12	2026-12-21	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2482	12	2026-12-22	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2483	12	2026-12-23	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2484	12	2026-12-24	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2485	12	2026-12-25	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2486	12	2026-12-28	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2487	12	2026-12-29	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2488	12	2026-12-30	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2489	12	2026-12-31	10:00:00	22:00:00	300.00	1	f	t	\N	2025-09-14 11:27:18.383435+00	2025-09-14 11:27:18.383435+00
2491	2	2025-09-18	10:00:00	22:00:00	250.00	1	f	t		2025-09-17 14:34:16.772675+00	2025-09-17 14:34:16.772675+00
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, telegram_id, username, first_name, last_name, phone, role, is_active, created_at, updated_at, roles) FROM stdin;
1	1220971779	Deniskada00	Den	Novikov	\N	owner	t	2025-08-28 03:56:17.522041+00	2025-08-28 03:56:17.522041+00	["owner"]
2	1657453440	utoptopia1	Александр	\N	\N	owner	t	2025-08-28 09:40:44.523761+00	2025-08-28 09:40:44.523761+00	["owner"]
3	1170536174	cvetutcvetyme	Цветут	Цветы	\N	owner	t	2025-08-28 13:49:58.630082+00	2025-08-28 13:49:58.630082+00	["owner"]
4	6562516971	\N	Анна	Новикова	\N	owner	t	2025-08-31 05:07:46.820585+00	2025-08-31 05:07:46.820585+00	["owner"]
5	12345	testuser	Test	User	\N	owner	t	2025-09-02 06:29:37.91967+00	2025-09-02 06:48:35.634524+00	["owner"]
6	5577223137	techpodru	Novikov	Den	\N	employee	t	2025-09-06 19:03:19.600465+00	2025-09-06 19:03:19.600465+00	["employee"]
8	999999999	testuser	Test	User	\N	owner	t	2025-09-10 17:54:07.134354+00	2025-09-10 17:54:07.134354+00	["applicant"]
7	1821645654	denisinovikov	D	N	\N	owner	t	2025-09-09 07:51:03.390651+00	2025-09-15 07:10:22.647074+00	["superadmin", "owner"]
\.


--
-- Data for Name: geocode_settings; Type: TABLE DATA; Schema: tiger; Owner: postgres
--

COPY tiger.geocode_settings (name, setting, unit, category, short_desc) FROM stdin;
\.


--
-- Data for Name: pagc_gaz; Type: TABLE DATA; Schema: tiger; Owner: postgres
--

COPY tiger.pagc_gaz (id, seq, word, stdword, token, is_custom) FROM stdin;
\.


--
-- Data for Name: pagc_lex; Type: TABLE DATA; Schema: tiger; Owner: postgres
--

COPY tiger.pagc_lex (id, seq, word, stdword, token, is_custom) FROM stdin;
\.


--
-- Data for Name: pagc_rules; Type: TABLE DATA; Schema: tiger; Owner: postgres
--

COPY tiger.pagc_rules (id, rule, is_custom) FROM stdin;
\.


--
-- Data for Name: topology; Type: TABLE DATA; Schema: topology; Owner: postgres
--

COPY topology.topology (id, name, srid, "precision", hasz) FROM stdin;
\.


--
-- Data for Name: layer; Type: TABLE DATA; Schema: topology; Owner: postgres
--

COPY topology.layer (topology_id, layer_id, schema_name, table_name, feature_column, feature_type, level, child_id) FROM stdin;
\.


--
-- Name: contract_templates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.contract_templates_id_seq', 2, true);


--
-- Name: contract_versions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.contract_versions_id_seq', 11, true);


--
-- Name: contracts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.contracts_id_seq', 13, true);


--
-- Name: objects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.objects_id_seq', 24, true);


--
-- Name: owner_profiles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.owner_profiles_id_seq', 1, true);


--
-- Name: planning_templates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.planning_templates_id_seq', 4, true);


--
-- Name: shift_schedules_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.shift_schedules_id_seq', 25, true);


--
-- Name: shifts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.shifts_id_seq', 35, true);


--
-- Name: tag_references_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tag_references_id_seq', 43, true);


--
-- Name: template_time_slots_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.template_time_slots_id_seq', 1, false);


--
-- Name: time_slots_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.time_slots_id_seq', 2491, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 8, true);


--
-- Name: topology_id_seq; Type: SEQUENCE SET; Schema: topology; Owner: postgres
--

SELECT pg_catalog.setval('topology.topology_id_seq', 1, false);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: contract_templates contract_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contract_templates
    ADD CONSTRAINT contract_templates_pkey PRIMARY KEY (id);


--
-- Name: contract_versions contract_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contract_versions
    ADD CONSTRAINT contract_versions_pkey PRIMARY KEY (id);


--
-- Name: contracts contracts_contract_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contracts
    ADD CONSTRAINT contracts_contract_number_key UNIQUE (contract_number);


--
-- Name: contracts contracts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contracts
    ADD CONSTRAINT contracts_pkey PRIMARY KEY (id);


--
-- Name: objects objects_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.objects
    ADD CONSTRAINT objects_pkey PRIMARY KEY (id);


--
-- Name: owner_profiles owner_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.owner_profiles
    ADD CONSTRAINT owner_profiles_pkey PRIMARY KEY (id);


--
-- Name: planning_templates planning_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.planning_templates
    ADD CONSTRAINT planning_templates_pkey PRIMARY KEY (id);


--
-- Name: shift_schedules shift_schedules_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shift_schedules
    ADD CONSTRAINT shift_schedules_pkey PRIMARY KEY (id);


--
-- Name: shifts shifts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shifts
    ADD CONSTRAINT shifts_pkey PRIMARY KEY (id);


--
-- Name: tag_references tag_references_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tag_references
    ADD CONSTRAINT tag_references_pkey PRIMARY KEY (id);


--
-- Name: template_time_slots template_time_slots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.template_time_slots
    ADD CONSTRAINT template_time_slots_pkey PRIMARY KEY (id);


--
-- Name: time_slots time_slots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.time_slots
    ADD CONSTRAINT time_slots_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_contract_templates_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_contract_templates_id ON public.contract_templates USING btree (id);


--
-- Name: ix_contract_templates_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_contract_templates_name ON public.contract_templates USING btree (name);


--
-- Name: ix_contract_versions_contract_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_contract_versions_contract_id ON public.contract_versions USING btree (contract_id);


--
-- Name: ix_contract_versions_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_contract_versions_id ON public.contract_versions USING btree (id);


--
-- Name: ix_contracts_contract_number; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_contracts_contract_number ON public.contracts USING btree (contract_number);


--
-- Name: ix_contracts_employee_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_contracts_employee_id ON public.contracts USING btree (employee_id);


--
-- Name: ix_contracts_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_contracts_id ON public.contracts USING btree (id);


--
-- Name: ix_contracts_owner_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_contracts_owner_id ON public.contracts USING btree (owner_id);


--
-- Name: ix_objects_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_objects_id ON public.objects USING btree (id);


--
-- Name: ix_objects_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_objects_name ON public.objects USING btree (name);


--
-- Name: ix_owner_profiles_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_owner_profiles_id ON public.owner_profiles USING btree (id);


--
-- Name: ix_owner_profiles_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_owner_profiles_user_id ON public.owner_profiles USING btree (user_id);


--
-- Name: ix_planning_templates_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_planning_templates_id ON public.planning_templates USING btree (id);


--
-- Name: ix_planning_templates_owner_telegram_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_planning_templates_owner_telegram_id ON public.planning_templates USING btree (owner_telegram_id);


--
-- Name: ix_shift_schedules_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shift_schedules_id ON public.shift_schedules USING btree (id);


--
-- Name: ix_shift_schedules_object_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shift_schedules_object_id ON public.shift_schedules USING btree (object_id);


--
-- Name: ix_shift_schedules_planned_end; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shift_schedules_planned_end ON public.shift_schedules USING btree (planned_end);


--
-- Name: ix_shift_schedules_planned_start; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shift_schedules_planned_start ON public.shift_schedules USING btree (planned_start);


--
-- Name: ix_shift_schedules_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shift_schedules_status ON public.shift_schedules USING btree (status);


--
-- Name: ix_shift_schedules_time_slot_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shift_schedules_time_slot_id ON public.shift_schedules USING btree (time_slot_id);


--
-- Name: ix_shift_schedules_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shift_schedules_user_id ON public.shift_schedules USING btree (user_id);


--
-- Name: ix_shifts_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shifts_id ON public.shifts USING btree (id);


--
-- Name: ix_shifts_object_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shifts_object_id ON public.shifts USING btree (object_id);


--
-- Name: ix_shifts_schedule_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shifts_schedule_id ON public.shifts USING btree (schedule_id);


--
-- Name: ix_shifts_start_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shifts_start_time ON public.shifts USING btree (start_time);


--
-- Name: ix_shifts_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shifts_status ON public.shifts USING btree (status);


--
-- Name: ix_shifts_time_slot_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shifts_time_slot_id ON public.shifts USING btree (time_slot_id);


--
-- Name: ix_shifts_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_shifts_user_id ON public.shifts USING btree (user_id);


--
-- Name: ix_tag_references_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tag_references_category ON public.tag_references USING btree (category);


--
-- Name: ix_tag_references_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tag_references_id ON public.tag_references USING btree (id);


--
-- Name: ix_tag_references_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_tag_references_key ON public.tag_references USING btree (key);


--
-- Name: ix_template_time_slots_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_template_time_slots_id ON public.template_time_slots USING btree (id);


--
-- Name: ix_time_slots_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_time_slots_id ON public.time_slots USING btree (id);


--
-- Name: ix_time_slots_object_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_time_slots_object_id ON public.time_slots USING btree (object_id);


--
-- Name: ix_time_slots_slot_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_time_slots_slot_date ON public.time_slots USING btree (slot_date);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_users_telegram_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_telegram_id ON public.users USING btree (telegram_id);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: contract_templates contract_templates_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contract_templates
    ADD CONSTRAINT contract_templates_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: contract_versions contract_versions_contract_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contract_versions
    ADD CONSTRAINT contract_versions_contract_id_fkey FOREIGN KEY (contract_id) REFERENCES public.contracts(id);


--
-- Name: contract_versions contract_versions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contract_versions
    ADD CONSTRAINT contract_versions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: contracts contracts_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contracts
    ADD CONSTRAINT contracts_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.users(id);


--
-- Name: contracts contracts_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contracts
    ADD CONSTRAINT contracts_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id);


--
-- Name: contracts contracts_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contracts
    ADD CONSTRAINT contracts_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.contract_templates(id);


--
-- Name: shifts fk_shifts_schedule_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shifts
    ADD CONSTRAINT fk_shifts_schedule_id FOREIGN KEY (schedule_id) REFERENCES public.shift_schedules(id);


--
-- Name: objects objects_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.objects
    ADD CONSTRAINT objects_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id);


--
-- Name: owner_profiles owner_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.owner_profiles
    ADD CONSTRAINT owner_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: planning_templates planning_templates_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.planning_templates
    ADD CONSTRAINT planning_templates_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects(id);


--
-- Name: shift_schedules shift_schedules_actual_shift_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shift_schedules
    ADD CONSTRAINT shift_schedules_actual_shift_id_fkey FOREIGN KEY (actual_shift_id) REFERENCES public.shifts(id);


--
-- Name: shift_schedules shift_schedules_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shift_schedules
    ADD CONSTRAINT shift_schedules_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects(id);


--
-- Name: shift_schedules shift_schedules_time_slot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shift_schedules
    ADD CONSTRAINT shift_schedules_time_slot_id_fkey FOREIGN KEY (time_slot_id) REFERENCES public.time_slots(id);


--
-- Name: shift_schedules shift_schedules_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shift_schedules
    ADD CONSTRAINT shift_schedules_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: shifts shifts_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shifts
    ADD CONSTRAINT shifts_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects(id);


--
-- Name: shifts shifts_time_slot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shifts
    ADD CONSTRAINT shifts_time_slot_id_fkey FOREIGN KEY (time_slot_id) REFERENCES public.time_slots(id);


--
-- Name: shifts shifts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shifts
    ADD CONSTRAINT shifts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: template_time_slots template_time_slots_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.template_time_slots
    ADD CONSTRAINT template_time_slots_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.planning_templates(id);


--
-- Name: time_slots time_slots_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.time_slots
    ADD CONSTRAINT time_slots_object_id_fkey FOREIGN KEY (object_id) REFERENCES public.objects(id);


--
-- PostgreSQL database dump complete
--

