"""
Модуль доменных сущностей StaffProBot
"""

# Импортируем модели в правильном порядке
from .base import Base
from .user import User
from .payment_system import PaymentSystem
from .payment_schedule import PaymentSchedule
from .org_structure import OrgStructureUnit
from .payroll_entry import PayrollEntry
from .payroll_adjustment import PayrollAdjustment
from .employee_payment import EmployeePayment
from .timeslot_task_template import TimeslotTaskTemplate
from .object_opening import ObjectOpening
from .object import Object
from .shift import Shift
from .shift_schedule import ShiftSchedule
from .time_slot import TimeSlot
from .tag_reference import TagReference
from .owner_profile import OwnerProfile
from .organization_profile import OrganizationProfile
from .system_feature import SystemFeature
from .contract import Contract
from .contract_termination import ContractTermination
from .manager_object_permission import ManagerObjectPermission
from .application import Application, ApplicationStatus
from .interview import Interview, InterviewType, InterviewStatus
from .task_category import TaskCategory
from .task_template import TaskTemplateV2
from .task_plan import TaskPlanV2
from .task_entry import TaskEntryV2
from .rule import Rule
from .incident import Incident
from .cancellation_reason import CancellationReason
from .tariff_plan import TariffPlan
from .user_subscription import UserSubscription, SubscriptionStatus, BillingPeriod
from .billing_transaction import BillingTransaction, TransactionType, TransactionStatus, PaymentMethod
from .usage_metrics import UsageMetrics
from .notification import Notification
from .payment_notification import PaymentNotification, NotificationType, NotificationStatus, NotificationChannel
from .review import Review, ReviewMedia, ReviewAppeal, Rating, SystemRule
from .bug_log import BugLog
from .changelog_entry import ChangelogEntry
from .deployment import Deployment
from .faq_entry import FAQEntry
from .shift_history import ShiftHistory

__all__ = [
    "Base",
    "User",
    "PaymentSystem",
    "PaymentSchedule",
    "OrgStructureUnit",
    "PayrollEntry",
    "PayrollAdjustment",
    "EmployeePayment",
    "TimeslotTaskTemplate",
    "ObjectOpening",
    "Object",
    "Shift",
    "ShiftSchedule",
    "TimeSlot",
    "TagReference",
    "OwnerProfile",
    "OrganizationProfile",
    "SystemFeature",
    "Contract",
    "ContractTermination",
    "ManagerObjectPermission",
    "Application",
    "ApplicationStatus",
    "Interview",
    "InterviewType",
    "InterviewStatus",
    "TaskCategory",
    "TaskTemplate",
    "TariffPlan",
    "UserSubscription",
    "SubscriptionStatus",
    "BillingPeriod",
    "BillingTransaction",
    "TransactionType",
    "TransactionStatus",
    "PaymentMethod",
    "UsageMetrics",
    "Notification",
    "PaymentNotification",
    "NotificationType",
    "NotificationStatus",
    "NotificationChannel",
    "Review",
    "ReviewMedia",
    "ReviewAppeal",
    "Rating",
    "SystemRule",
    "BugLog",
    "ChangelogEntry",
    "Deployment",
    "FAQEntry",
    "ShiftHistory",
]
