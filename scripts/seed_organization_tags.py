"""
Seed-скрипт для добавления тегов реквизитов организаций.

Добавляет теги для полей ИП и ЮЛ из org_data.md.
"""

import asyncio
import sys
import os

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import select
from core.database.session import get_async_session
from domain.entities.tag_reference import TagReference
from core.logging.logger import logger


# Теги для ИП (Физическое лицо)
INDIVIDUAL_TAGS = [
    {
        'key': 'owner_fullname',
        'label': 'ФИО',
        'description': 'Полные фамилия, имя и отчество индивидуального предпринимателя',
        'data_type': 'text',
        'is_required': True,
        'sort_order': 1
    },
    {
        'key': 'owner_ogrnip',
        'label': 'ОГРНИП',
        'description': 'Основной государственный регистрационный номер ИП',
        'data_type': 'text',
        'is_required': True,
        'validation_pattern': r'^\d{15}$',
        'validation_message': 'ОГРНИП должен состоять из 15 цифр',
        'sort_order': 2
    },
    {
        'key': 'owner_inn',
        'label': 'ИНН',
        'description': 'Идентификационный номер налогоплательщика',
        'data_type': 'text',
        'is_required': True,
        'validation_pattern': r'^\d{12}$',
        'validation_message': 'ИНН ИП должен состоять из 12 цифр',
        'sort_order': 3
    },
    {
        'key': 'owner_okved',
        'label': 'ОКВЭД',
        'description': 'Код вида экономической деятельности',
        'data_type': 'text',
        'is_required': False,
        'sort_order': 4
    },
    {
        'key': 'owner_phone',
        'label': 'Телефон',
        'description': 'Контактный телефон предпринимателя',
        'data_type': 'text',
        'is_required': False,
        'sort_order': 5
    },
    {
        'key': 'owner_email',
        'label': 'E-mail',
        'description': 'Электронная почта предпринимателя',
        'data_type': 'email',
        'is_required': False,
        'sort_order': 6
    },
    {
        'key': 'owner_registration_address',
        'label': 'Адрес регистрации',
        'description': 'Адрес регистрации ИП',
        'data_type': 'textarea',
        'is_required': False,
        'sort_order': 7
    },
    {
        'key': 'owner_postal_address',
        'label': 'Почтовый адрес',
        'description': 'Почтовый адрес для корреспонденции',
        'data_type': 'textarea',
        'is_required': False,
        'sort_order': 8
    },
    {
        'key': 'owner_account_number',
        'label': 'Расчетный счет',
        'description': 'Номер расчетного счета',
        'data_type': 'text',
        'is_required': False,
        'validation_pattern': r'^\d{20}$',
        'validation_message': 'Расчетный счет должен состоять из 20 цифр',
        'sort_order': 9
    },
    {
        'key': 'owner_bik',
        'label': 'БИК банка',
        'description': 'Банковский идентификационный код',
        'data_type': 'text',
        'is_required': False,
        'validation_pattern': r'^\d{9}$',
        'validation_message': 'БИК должен состоять из 9 цифр',
        'sort_order': 10
    },
    {
        'key': 'owner_correspondent_account',
        'label': 'Корреспондентский счет',
        'description': 'Корреспондентский счет банка',
        'data_type': 'text',
        'is_required': False,
        'validation_pattern': r'^\d{20}$',
        'validation_message': 'Корр. счет должен состоять из 20 цифр',
        'sort_order': 11
    },
]

# Теги для ЮЛ (Юридическое лицо)
LEGAL_TAGS = [
    {
        'key': 'company_full_name',
        'label': 'Наименование организации',
        'description': 'Полное наименование юридического лица',
        'data_type': 'text',
        'is_required': True,
        'sort_order': 1
    },
    {
        'key': 'company_short_name',
        'label': 'Краткое наименование',
        'description': 'Краткое наименование организации',
        'data_type': 'text',
        'is_required': False,
        'sort_order': 2
    },
    {
        'key': 'company_ogrn',
        'label': 'ОГРН',
        'description': 'Основной государственный регистрационный номер',
        'data_type': 'text',
        'is_required': True,
        'validation_pattern': r'^\d{13}$',
        'validation_message': 'ОГРН должен состоять из 13 цифр',
        'sort_order': 3
    },
    {
        'key': 'company_inn',
        'label': 'ИНН',
        'description': 'Идентификационный номер налогоплательщика',
        'data_type': 'text',
        'is_required': True,
        'validation_pattern': r'^\d{10}$',
        'validation_message': 'ИНН ЮЛ должен состоять из 10 цифр',
        'sort_order': 4
    },
    {
        'key': 'company_kpp',
        'label': 'КПП',
        'description': 'Код причины постановки на учет',
        'data_type': 'text',
        'is_required': True,
        'validation_pattern': r'^\d{9}$',
        'validation_message': 'КПП должен состоять из 9 цифр',
        'sort_order': 5
    },
    {
        'key': 'company_legal_address',
        'label': 'Юридический адрес',
        'description': 'Юридический адрес организации',
        'data_type': 'textarea',
        'is_required': False,
        'sort_order': 6
    },
    {
        'key': 'company_postal_address',
        'label': 'Почтовый адрес',
        'description': 'Почтовый адрес для корреспонденции',
        'data_type': 'textarea',
        'is_required': False,
        'sort_order': 7
    },
    {
        'key': 'company_okpo',
        'label': 'ОКПО',
        'description': 'Общероссийский классификатор предприятий и организаций',
        'data_type': 'text',
        'is_required': False,
        'sort_order': 8
    },
    {
        'key': 'company_okved',
        'label': 'ОКВЭД',
        'description': 'Код вида экономической деятельности',
        'data_type': 'text',
        'is_required': False,
        'sort_order': 9
    },
    {
        'key': 'company_account_number',
        'label': 'Расчетный счет',
        'description': 'Номер расчетного счета',
        'data_type': 'text',
        'is_required': False,
        'validation_pattern': r'^\d{20}$',
        'validation_message': 'Расчетный счет должен состоять из 20 цифр',
        'sort_order': 10
    },
    {
        'key': 'company_bik',
        'label': 'БИК банка',
        'description': 'Банковский идентификационный код',
        'data_type': 'text',
        'is_required': False,
        'validation_pattern': r'^\d{9}$',
        'validation_message': 'БИК должен состоять из 9 цифр',
        'sort_order': 11
    },
    {
        'key': 'company_correspondent_account',
        'label': 'Корреспондентский счет',
        'description': 'Корреспондентский счет банка',
        'data_type': 'text',
        'is_required': False,
        'validation_pattern': r'^\d{20}$',
        'validation_message': 'Корр. счет должен состоять из 20 цифр',
        'sort_order': 12
    },
    {
        'key': 'company_director_position',
        'label': 'Должность руководителя',
        'description': 'Должность руководителя организации',
        'data_type': 'text',
        'is_required': False,
        'sort_order': 13
    },
    {
        'key': 'company_director_fullname',
        'label': 'ФИО руководителя',
        'description': 'Полные фамилия, имя и отчество руководителя',
        'data_type': 'text',
        'is_required': False,
        'sort_order': 14
    },
    {
        'key': 'company_basis',
        'label': 'Действует на основании',
        'description': 'Документ-основание полномочий (Устав, Доверенность и т.д.)',
        'data_type': 'text',
        'is_required': False,
        'sort_order': 15
    },
]


async def seed_organization_tags():
    """Добавить теги для реквизитов организаций."""
    async with get_async_session() as session:
        logger.info("Начало добавления тегов реквизитов организаций")
        
        # Получаем все существующие теги
        result = await session.execute(select(TagReference))
        existing_tags = {t.key: t for t in result.scalars().all()}
        
        added_count = 0
        updated_count = 0
        
        # Добавляем теги для ИП
        logger.info("Добавление тегов для ИП...")
        for tag_data in INDIVIDUAL_TAGS:
            if tag_data['key'] in existing_tags:
                # Обновляем существующий
                tag = existing_tags[tag_data['key']]
                for key, value in tag_data.items():
                    if key != 'key':
                        setattr(tag, key, value)
                tag.category = 'organization_requisites'
                updated_count += 1
                logger.info(f"  Обновлен тег: {tag_data['key']}")
            else:
                # Создаём новый
                tag = TagReference(
                    category='organization_requisites',
                    **tag_data
                )
                session.add(tag)
                added_count += 1
                logger.info(f"  Создан тег: {tag_data['key']}")
        
        # Добавляем теги для ЮЛ
        logger.info("Добавление тегов для ЮЛ...")
        for tag_data in LEGAL_TAGS:
            if tag_data['key'] in existing_tags:
                # Обновляем существующий
                tag = existing_tags[tag_data['key']]
                for key, value in tag_data.items():
                    if key != 'key':
                        setattr(tag, key, value)
                tag.category = 'organization_requisites'
                updated_count += 1
                logger.info(f"  Обновлен тег: {tag_data['key']}")
            else:
                # Создаём новый
                tag = TagReference(
                    category='organization_requisites',
                    **tag_data
                )
                session.add(tag)
                added_count += 1
                logger.info(f"  Создан тег: {tag_data['key']}")
        
        await session.commit()
        logger.info(f"Добавление тегов завершено. Создано: {added_count}, обновлено: {updated_count}")


if __name__ == "__main__":
    asyncio.run(seed_organization_tags())

