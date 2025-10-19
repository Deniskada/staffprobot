"""
Сервис для работы со справочником тегов и профилями владельцев.

Предоставляет методы для управления тегами, создания профилей
и интеграции с системой шаблонов договоров.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from domain.entities.tag_reference import TagReference
from domain.entities.owner_profile import OwnerProfile
from domain.entities.user import User

logger = logging.getLogger(__name__)


class TagService:
    """Сервис для работы с тегами и профилями."""
    
    async def create_default_tags(self, session: AsyncSession) -> None:
        """Создать справочник тегов по умолчанию для России."""
        
        default_tags = [
            # === СИСТЕМНЫЕ ТЕГИ ===
            {
                'key': 'current_date',
                'label': 'Текущая дата',
                'description': 'Автоматически подставляется текущая дата в формате ДД.ММ.ГГГГ',
                'category': 'system',
                'data_type': 'text',
                'is_system': True,
                'is_required': False,
                'sort_order': 1000
            },
            {
                'key': 'current_time',
                'label': 'Текущее время',
                'description': 'Автоматически подставляется текущее время в формате ЧЧ:ММ',
                'category': 'system',
                'data_type': 'text',
                'is_system': True,
                'is_required': False,
                'sort_order': 1001
            },
            {
                'key': 'current_year',
                'label': 'Текущий год',
                'description': 'Автоматически подставляется текущий год в формате ГГГГ',
                'category': 'system',
                'data_type': 'text',
                'is_system': True,
                'is_required': False,
                'sort_order': 1002
            },
            
            # === ТЕГИ ВЛАДЕЛЬЦА/ЗАКАЗЧИКА ===
            {
                'key': 'owner_name',
                'label': 'Имя владельца',
                'description': 'Имя владельца бизнеса/заказчика',
                'category': 'owner',
                'data_type': 'text',
                'is_required': True,
                'sort_order': 100
            },
            {
                'key': 'owner_last_name',
                'label': 'Фамилия владельца',
                'description': 'Фамилия владельца бизнеса/заказчика',
                'category': 'owner',
                'data_type': 'text',
                'is_required': True,
                'sort_order': 101
            },
            {
                'key': 'owner_middle_name',
                'label': 'Отчество владельца',
                'description': 'Отчество владельца бизнеса/заказчика',
                'category': 'owner',
                'data_type': 'text',
                'is_required': False,
                'sort_order': 102
            },
            {
                'key': 'owner_full_name',
                'label': 'ФИО владельца полностью',
                'description': 'Полное ФИО владельца в формате "Фамилия Имя Отчество"',
                'category': 'owner',
                'data_type': 'text',
                'is_required': False,
                'sort_order': 103
            },
            {
                'key': 'owner_birth_date',
                'label': 'Дата рождения владельца',
                'description': 'Дата рождения владельца',
                'category': 'owner',
                'data_type': 'date',
                'is_required': False,
                'sort_order': 104
            },
            {
                'key': 'owner_inn',
                'label': 'ИНН владельца',
                'description': 'Индивидуальный налоговый номер владельца',
                'category': 'owner',
                'data_type': 'text',
                'is_required': False,
                'validation_pattern': r'^\d{10}|\d{12}$',
                'validation_message': 'ИНН должен содержать 10 или 12 цифр',
                'sort_order': 105
            },
            {
                'key': 'owner_snils',
                'label': 'СНИЛС владельца',
                'description': 'Страховой номер индивидуального лицевого счета владельца',
                'category': 'owner',
                'data_type': 'text',
                'is_required': False,
                'validation_pattern': r'^\d{3}-\d{3}-\d{3} \d{2}$',
                'validation_message': 'СНИЛС должен быть в формате XXX-XXX-XXX XX',
                'sort_order': 106
            },
            {
                'key': 'owner_phone',
                'label': 'Телефон владельца',
                'description': 'Контактный телефон владельца',
                'category': 'owner',
                'data_type': 'text',
                'is_required': False,
                'validation_pattern': r'^\+7\d{10}$',
                'validation_message': 'Телефон должен быть в формате +7XXXXXXXXXX',
                'sort_order': 107
            },
            {
                'key': 'owner_email',
                'label': 'Email владельца',
                'description': 'Электронная почта владельца',
                'category': 'owner',
                'data_type': 'email',
                'is_required': False,
                'sort_order': 108
            },
            
            # === ТЕГИ КОМПАНИИ ===
            {
                'key': 'company_name',
                'label': 'Название компании',
                'description': 'Полное наименование организации',
                'category': 'company',
                'data_type': 'text',
                'is_required': False,
                'sort_order': 200
            },
            {
                'key': 'company_short_name',
                'label': 'Краткое название компании',
                'description': 'Сокращенное наименование организации',
                'category': 'company',
                'data_type': 'text',
                'is_required': False,
                'sort_order': 201
            },
            {
                'key': 'company_inn',
                'label': 'ИНН компании',
                'description': 'Индивидуальный налоговый номер организации',
                'category': 'company',
                'data_type': 'text',
                'is_required': False,
                'validation_pattern': r'^\d{10}$',
                'validation_message': 'ИНН организации должен содержать 10 цифр',
                'sort_order': 202
            },
            {
                'key': 'company_kpp',
                'label': 'КПП компании',
                'description': 'Код причины постановки на учет',
                'category': 'company',
                'data_type': 'text',
                'is_required': False,
                'validation_pattern': r'^\d{9}$',
                'validation_message': 'КПП должен содержать 9 цифр',
                'sort_order': 203
            },
            {
                'key': 'company_ogrn',
                'label': 'ОГРН компании',
                'description': 'Основной государственный регистрационный номер',
                'category': 'company',
                'data_type': 'text',
                'is_required': False,
                'validation_pattern': r'^\d{13}|\d{15}$',
                'validation_message': 'ОГРН должен содержать 13 или 15 цифр',
                'sort_order': 204
            },
            {
                'key': 'company_address',
                'label': 'Адрес компании',
                'description': 'Юридический адрес организации',
                'category': 'company',
                'data_type': 'textarea',
                'is_required': False,
                'sort_order': 205
            },
            {
                'key': 'company_bank_name',
                'label': 'Название банка',
                'description': 'Наименование банка для расчетного счета',
                'category': 'company',
                'data_type': 'text',
                'is_required': False,
                'sort_order': 206
            },
            {
                'key': 'company_bank_account',
                'label': 'Расчетный счет',
                'description': 'Номер расчетного счета в банке',
                'category': 'company',
                'data_type': 'text',
                'is_required': False,
                'validation_pattern': r'^\d{20}$',
                'validation_message': 'Расчетный счет должен содержать 20 цифр',
                'sort_order': 207
            },
            {
                'key': 'company_bank_bik',
                'label': 'БИК банка',
                'description': 'Банковский идентификационный код',
                'category': 'company',
                'data_type': 'text',
                'is_required': False,
                'validation_pattern': r'^\d{9}$',
                'validation_message': 'БИК должен содержать 9 цифр',
                'sort_order': 208
            },
            {
                'key': 'company_bank_corr_account',
                'label': 'Корреспондентский счет',
                'description': 'Корреспондентский счет банка',
                'category': 'company',
                'data_type': 'text',
                'is_required': False,
                'validation_pattern': r'^\d{20}$',
                'validation_message': 'Корреспондентский счет должен содержать 20 цифр',
                'sort_order': 209
            },
            
            # === ТЕГИ СОТРУДНИКА ===
            {
                'key': 'employee_name',
                'label': 'Имя сотрудника',
                'description': 'Имя сотрудника/исполнителя',
                'category': 'employee',
                'data_type': 'text',
                'is_required': True,
                'sort_order': 300
            },
            {
                'key': 'employee_last_name',
                'label': 'Фамилия сотрудника',
                'description': 'Фамилия сотрудника/исполнителя',
                'category': 'employee',
                'data_type': 'text',
                'is_required': False,
                'sort_order': 301
            },
            {
                'key': 'employee_middle_name',
                'label': 'Отчество сотрудника',
                'description': 'Отчество сотрудника/исполнителя',
                'category': 'employee',
                'data_type': 'text',
                'is_required': False,
                'sort_order': 302
            },
            {
                'key': 'birth_date',
                'label': 'Дата рождения сотрудника',
                'description': 'Дата рождения сотрудника',
                'category': 'employee',
                'data_type': 'date',
                'is_required': False,
                'sort_order': 303
            },
            {
                'key': 'inn',
                'label': 'ИНН сотрудника',
                'description': 'Индивидуальный налоговый номер сотрудника',
                'category': 'employee',
                'data_type': 'text',
                'is_required': False,
                'validation_pattern': r'^\d{12}$',
                'validation_message': 'ИНН физического лица должен содержать 12 цифр',
                'sort_order': 304
            },
            {
                'key': 'snils',
                'label': 'СНИЛС сотрудника',
                'description': 'Страховой номер индивидуального лицевого счета сотрудника',
                'category': 'employee',
                'data_type': 'text',
                'is_required': False,
                'validation_pattern': r'^\d{3}-\d{3}-\d{3} \d{2}$',
                'validation_message': 'СНИЛС должен быть в формате XXX-XXX-XXX XX',
                'sort_order': 305
            },
            {
                'key': 'passport_series',
                'label': 'Серия паспорта',
                'description': 'Серия паспорта сотрудника',
                'category': 'employee',
                'data_type': 'text',
                'is_required': False,
                'validation_pattern': r'^\d{4}$',
                'validation_message': 'Серия паспорта должна содержать 4 цифры',
                'sort_order': 306
            },
            {
                'key': 'passport_number',
                'label': 'Номер паспорта',
                'description': 'Номер паспорта сотрудника',
                'category': 'employee',
                'data_type': 'text',
                'is_required': False,
                'validation_pattern': r'^\d{6}$',
                'validation_message': 'Номер паспорта должен содержать 6 цифр',
                'sort_order': 307
            },
            {
                'key': 'passport_issued_by',
                'label': 'Кем выдан паспорт',
                'description': 'Орган, выдавший паспорт',
                'category': 'employee',
                'data_type': 'textarea',
                'is_required': False,
                'sort_order': 308
            },
            {
                'key': 'passport_issue_date',
                'label': 'Дата выдачи паспорта',
                'description': 'Дата выдачи паспорта',
                'category': 'employee',
                'data_type': 'date',
                'is_required': False,
                'sort_order': 309
            },
            {
                'key': 'passport_department_code',
                'label': 'Код подразделения',
                'description': 'Код подразделения, выдавшего паспорт',
                'category': 'employee',
                'data_type': 'text',
                'is_required': False,
                'validation_pattern': r'^\d{3}-\d{3}$',
                'validation_message': 'Код подразделения должен быть в формате XXX-XXX',
                'sort_order': 310
            },
            {
                'key': 'registration_address',
                'label': 'Адрес регистрации',
                'description': 'Адрес регистрации сотрудника по паспорту',
                'category': 'employee',
                'data_type': 'textarea',
                'is_required': False,
                'sort_order': 311
            },
            {
                'key': 'employee_phone',
                'label': 'Телефон сотрудника',
                'description': 'Контактный телефон сотрудника',
                'category': 'employee',
                'data_type': 'text',
                'is_required': False,
                'validation_pattern': r'^\+7\d{10}$',
                'validation_message': 'Телефон должен быть в формате +7XXXXXXXXXX',
                'sort_order': 312
            },
            {
                'key': 'employee_email',
                'label': 'Email сотрудника',
                'description': 'Электронная почта сотрудника',
                'category': 'employee',
                'data_type': 'email',
                'is_required': False,
                'sort_order': 313
            },
            
            # === ДОГОВОРНЫЕ ТЕГИ ===
            {
                'key': 'contract_number',
                'label': 'Номер договора',
                'description': 'Номер заключаемого договора',
                'category': 'contract',
                'data_type': 'text',
                'is_required': False,
                'sort_order': 400
            },
            {
                'key': 'contract_date',
                'label': 'Дата договора',
                'description': 'Дата заключения договора',
                'category': 'contract',
                'data_type': 'date',
                'is_required': False,
                'sort_order': 401
            },
            {
                'key': 'contract_start_date',
                'label': 'Дата начала действия',
                'description': 'Дата начала действия договора',
                'category': 'contract',
                'data_type': 'date',
                'is_required': False,
                'sort_order': 402
            },
            {
                'key': 'contract_end_date',
                'label': 'Дата окончания',
                'description': 'Дата окончания действия договора',
                'category': 'contract',
                'data_type': 'date',
                'is_required': False,
                'sort_order': 403
            },
            {
                'key': 'contract_amount',
                'label': 'Сумма договора',
                'description': 'Общая сумма по договору',
                'category': 'contract',
                'data_type': 'number',
                'is_required': False,
                'sort_order': 404
            },
            {
                'key': 'hourly_rate',
                'label': 'Часовая ставка',
                'description': 'Размер оплаты за час работы',
                'category': 'contract',
                'data_type': 'number',
                'is_required': False,
                'sort_order': 405
            },
            {
                'key': 'work_description',
                'label': 'Описание работ',
                'description': 'Подробное описание выполняемых работ',
                'category': 'contract',
                'data_type': 'textarea',
                'is_required': False,
                'sort_order': 406
            }
        ]
        
        # Создаем теги, если их еще нет
        for tag_data in default_tags:
            query = select(TagReference).where(TagReference.key == tag_data['key'])
            result = await session.execute(query)
            existing_tag = result.scalar_one_or_none()
            
            if not existing_tag:
                tag = TagReference(**tag_data)
                session.add(tag)
                logger.info(f"Created tag: {tag_data['key']}")
        
        await session.commit()
        logger.info(f"Created {len(default_tags)} default tags")
    
    async def get_tags_by_category(self, session: AsyncSession, category: str = None) -> List[TagReference]:
        """Получить теги по категории."""
        query = select(TagReference).where(TagReference.is_active == True)
        
        if category:
            query = query.where(TagReference.category == category)
        
        query = query.order_by(TagReference.sort_order, TagReference.label)
        result = await session.execute(query)
        return result.scalars().all()
    
    async def get_all_tags(self, session: AsyncSession) -> List[TagReference]:
        """Получить все активные теги."""
        return await self.get_tags_by_category(session)
    
    async def get_tags_for_profile(self, session: AsyncSession, legal_type: str = "individual") -> List[TagReference]:
        """Получить теги для профиля владельца в зависимости от типа (ФЛ/ЮЛ)."""
        categories = ['owner', 'system']
        
        if legal_type == "legal":
            categories.append('company')
        
        query = select(TagReference).where(
            and_(
                TagReference.is_active == True,
                TagReference.category.in_(categories)
            )
        ).order_by(TagReference.sort_order, TagReference.label)
        
        result = await session.execute(query)
        return result.scalars().all()
    
    async def create_or_update_owner_profile(
        self,
        session: AsyncSession,
        user_id: int,
        profile_data: Dict[str, Any],
        legal_type: str = "individual"
    ) -> OwnerProfile:
        """Создать или обновить профиль владельца."""
        
        # Ищем существующий профиль
        query = select(OwnerProfile).where(OwnerProfile.user_id == user_id)
        result = await session.execute(query)
        profile = result.scalar_one_or_none()
        
        if not profile:
            # Создаем новый профиль
            profile = OwnerProfile(
                user_id=user_id,
                legal_type=legal_type,
                profile_data=profile_data.get('profile_data', {}),
                active_tags=profile_data.get('active_tags', [])
            )
            session.add(profile)
            logger.info(f"Created owner profile for user {user_id}")
        else:
            # Обновляем существующий
            profile.legal_type = legal_type
            profile.profile_data = profile_data.get('profile_data', {})
            profile.active_tags = profile_data.get('active_tags', [])
            logger.info(f"Updated owner profile for user {user_id}")
        
        # Устанавливаем другие поля
        if 'profile_name' in profile_data:
            profile.profile_name = profile_data['profile_name']
        
        if 'is_public' in profile_data:
            profile.is_public = profile_data['is_public']
        
        # Новые поля профиля
        if 'about_company' in profile_data:
            profile.about_company = profile_data['about_company']
        
        if 'values' in profile_data:
            profile.values = profile_data['values']
        
        if 'photos' in profile_data:
            profile.photos = profile_data['photos']
        
        if 'contact_phone' in profile_data:
            profile.contact_phone = profile_data['contact_phone']
        
        if 'contact_messengers' in profile_data:
            profile.contact_messengers = profile_data['contact_messengers']
        
        if 'enabled_features' in profile_data:
            profile.enabled_features = profile_data['enabled_features']
        
        # Проверяем полноту заполнения
        required_tags = await self._get_required_tags_for_legal_type(session, legal_type)
        completion = profile.get_completion_percentage([tag.key for tag in required_tags])
        profile.is_complete = completion >= 80.0  # Считаем профиль полным при 80%+ заполнении
        
        await session.commit()
        await session.refresh(profile)
        return profile
    
    async def get_owner_profile(self, session: AsyncSession, user_id: int) -> Optional[OwnerProfile]:
        """Получить профиль владельца."""
        query = select(OwnerProfile).where(OwnerProfile.user_id == user_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_required_tags_for_legal_type(self, session: AsyncSession, legal_type: str) -> List[TagReference]:
        """Получить обязательные теги для типа собственника."""
        categories = ['owner']
        if legal_type == "legal":
            categories.append('company')
        
        query = select(TagReference).where(
            and_(
                TagReference.is_active == True,
                TagReference.is_required == True,
                TagReference.category.in_(categories)
            )
        )
        
        result = await session.execute(query)
        return result.scalars().all()
