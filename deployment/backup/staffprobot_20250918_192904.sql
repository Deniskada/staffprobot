--
-- PostgreSQL database dump
--

\restrict 5gDhaUjS9jooL3ZRYsjA6YPPWXCESeRBXDGshQa0NUO1hP8H1tp4ETU3J2hitQ0

-- Dumped from database version 15.4 (Debian 15.4-1.pgdg110+1)
-- Dumped by pg_dump version 15.14

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
    work_days_mask integer DEFAULT 31 NOT NULL,
    schedule_repeat_weeks integer DEFAULT 1 NOT NULL,
    available_for_applicants boolean,
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
    max_employees integer DEFAULT 1,
    is_additional boolean DEFAULT false,
    is_active boolean DEFAULT true,
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
    roles jsonb DEFAULT '[]'::jsonb NOT NULL
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
merge_20250918_end
\.


--
-- Data for Name: contract_templates; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.contract_templates (id, name, description, content, version, is_active, created_by, created_at, updated_at, is_public, fields_schema) FROM stdin;
\.


--
-- Data for Name: contract_versions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.contract_versions (id, contract_id, version_number, content, changes_description, created_by, created_at) FROM stdin;
\.


--
-- Data for Name: contracts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.contracts (id, contract_number, owner_id, employee_id, template_id, title, content, hourly_rate, start_date, end_date, status, is_active, allowed_objects, created_at, updated_at, signed_at, terminated_at, "values") FROM stdin;
\.


--
-- Data for Name: objects; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.objects (id, name, owner_id, address, coordinates, opening_time, closing_time, hourly_rate, required_employees, is_active, created_at, updated_at, max_distance_meters, auto_close_minutes, work_days_mask, schedule_repeat_weeks, available_for_applicants, timezone) FROM stdin;
\.


--
-- Data for Name: owner_profiles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.owner_profiles (id, user_id, profile_name, legal_type, profile_data, active_tags, is_complete, is_public, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: planning_templates; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.planning_templates (id, name, description, owner_telegram_id, object_id, is_active, is_public, start_time, end_time, hourly_rate, repeat_type, repeat_days, repeat_interval, repeat_end_date, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: shift_schedules; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.shift_schedules (id, user_id, object_id, planned_start, planned_end, status, hourly_rate, notes, notification_sent, actual_shift_id, created_at, updated_at, auto_closed, time_slot_id) FROM stdin;
\.


--
-- Data for Name: shifts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.shifts (id, user_id, object_id, start_time, end_time, status, start_coordinates, end_coordinates, total_hours, hourly_rate, total_payment, notes, created_at, updated_at, time_slot_id, schedule_id, is_planned) FROM stdin;
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
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, telegram_id, username, first_name, last_name, phone, role, is_active, created_at, updated_at, roles) FROM stdin;
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

SELECT pg_catalog.setval('public.contract_templates_id_seq', 1, false);


--
-- Name: contract_versions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.contract_versions_id_seq', 1, false);


--
-- Name: contracts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.contracts_id_seq', 1, false);


--
-- Name: objects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.objects_id_seq', 1, false);


--
-- Name: owner_profiles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.owner_profiles_id_seq', 1, false);


--
-- Name: planning_templates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.planning_templates_id_seq', 1, false);


--
-- Name: shift_schedules_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.shift_schedules_id_seq', 1, false);


--
-- Name: shifts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.shifts_id_seq', 1, false);


--
-- Name: tag_references_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tag_references_id_seq', 1, false);


--
-- Name: template_time_slots_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.template_time_slots_id_seq', 1, false);


--
-- Name: time_slots_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.time_slots_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 1, false);


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
-- Name: ix_time_slots_object_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_time_slots_object_id ON public.time_slots USING btree (object_id);


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

\unrestrict 5gDhaUjS9jooL3ZRYsjA6YPPWXCESeRBXDGshQa0NUO1hP8H1tp4ETU3J2hitQ0

