"""Stateless core building blocks for the next `pydmp` architecture.

This package is intentionally separate from the older stateful `pydmp`
surface. It provides a panel-scoped command-session manager, transport, and
session profiles that can be used by higher layers without owning panel state.

Most callers should import from `pydmp.core` instead of reaching into the
individual module files. This export surface is meant to be the readable,
stable entry point for the new core.
"""

# Exceptions and shared error types.
from .errors import (
    CommandSessionError,
    ListenerConfigurationError,
    ListenerError,
    ListenerProtocolError,
    SessionClosedError,
    SessionConnectError,
    SessionHandshakeError,
    SessionProfileNotImplementedError,
    SessionProtocolError,
    SessionTimeoutError,
    TransactionParseError,
)

# Area query and control transactions.
from .area_control import (
    AreaControlReply,
    TransactionArmAreas,
    TransactionDisarmAreas,
    normalize_area_list,
    parse_area_arm_reply,
    parse_area_disarm_reply,
)
from .area_settings import (
    AreaSettingsPage,
    AreaSettingsRecord,
    AreaSettingsReply,
    TransactionQueryAreaSettings,
    normalize_area_settings_number,
    parse_area_settings_page,
    parse_area_settings_reply,
)
from .area_status import (
    AreaStatusBlock,
    AreaStatusPage,
    AreaStatusRecord,
    AreaStatusReply,
    TransactionQueryAreas,
    parse_area_status_block,
    parse_area_status_page,
)

# Beginner-friendly client and manager entry points.
from .client import CorePanelClient
from .manager import CommandSessionManager

# Small read transactions.
from .lockout_code import (
    LockoutCodeReply,
    TransactionQueryLockoutCode,
    parse_lockout_code_reply,
)
from .sensor_reset import (
    SensorResetReply,
    TransactionSensorReset,
    parse_sensor_reset_reply,
)
from .system_options import (
    SystemOptionsReply,
    TransactionQuerySystemOptions,
    parse_system_options_reply,
)

# Push listener surface.
from .listener import (
    DMPPushListener,
    ListenerProfilePush,
    PushParsedAccessEvent,
    PushEvent,
    PushParsedCheckinEvent,
    PushParsedScheduleEvent,
    PushParsedTaggedEvent,
    PushParsedUserCodeEvent,
    PushParsedZoneEvent,
    PushMessage,
    PushSpecialFrame,
    PushTransportMode,
    parse_push_event,
)

# Shared transaction/session models.
from .models import (
    CompletionPolicy,
    PanelEndpoint,
    ReplyExpectation,
    SessionMode,
    Transaction,
    TransactionParser,
    ack_or_deny,
    no_reply_expected,
    payload_required,
    reply_optional,
)

# Output read and write transactions.
from .output_control import (
    OutputControlMode,
    OutputControlReply,
    TransactionAlarmSilence,
    TransactionSetOutput,
    normalize_output_control_mode,
    parse_alarm_silence_reply,
    parse_output_control_reply,
)
from .output_information import (
    OutputInformationPage,
    OutputInformationRecord,
    OutputInformationReply,
    TransactionQueryOutputInformation,
    normalize_output_information_selector,
    parse_output_information_page,
)
from .output_status import (
    OutputStatusPage,
    OutputStatusRecord,
    OutputStatusReply,
    TransactionQueryOutputs,
    TransactionQuerySpecificOutputs,
    normalize_output_selectors,
    normalize_output_selector,
    parse_output_status_page,
)

# Zone and area settings transactions.
from .profiles import (
    ProfilePage,
    ProfileRecord,
    ProfileReply,
    TransactionQueryProfiles,
    parse_profile_page,
)
from .zone_settings import (
    ZoneSettingsPage,
    ZoneSettingsRecord,
    ZoneSettingsReply,
    TransactionQueryZoneSettings,
    normalize_zone_settings_number,
    parse_zone_settings_page,
    parse_zone_settings_reply,
)

# Session profile implementations.
from .sessions import (
    SessionProfile,
    SessionProfileBlankV2,
    SessionProfileKeyedV2,
    SessionProfileSecureS,
    SessionProfileV30,
    SessionProfileV31,
    build_session_profile,
)

# Raw transport implementation.
from .transport import PanelTransport

# User table and zone query/control transactions.
from .users import (
    TransactionQueryUsers,
    UserFlags,
    UserRecord,
    UserReply,
    normalize_user_number,
    parse_user_page,
)
from .zone_status import (
    TransactionQueryAllAreasAndZones,
    TransactionQuerySpecificZones,
    TransactionQueryZones,
    ZoneStatusPage,
    ZoneStatusRecord,
    ZoneStatusReply,
    normalize_zone_query_area,
    normalize_zone_query_selector,
    parse_zone_status_page,
)
from .zone_control import (
    TransactionBypassZone,
    TransactionUnbypassZone,
    ZoneControlReply,
    normalize_zone_number,
    parse_zone_bypass_reply,
    parse_zone_unbypass_reply,
)

# Re-export the intended public surface of the stateless core.
__all__ = [
    "CommandSessionError",
    "ListenerError",
    "ListenerConfigurationError",
    "ListenerProtocolError",
    "SessionClosedError",
    "SessionConnectError",
    "SessionHandshakeError",
    "SessionProfileNotImplementedError",
    "SessionProtocolError",
    "SessionTimeoutError",
    "TransactionParseError",
    "AreaControlReply",
    "TransactionArmAreas",
    "TransactionDisarmAreas",
    "normalize_area_list",
    "parse_area_arm_reply",
    "parse_area_disarm_reply",
    "AreaSettingsPage",
    "AreaSettingsRecord",
    "AreaSettingsReply",
    "TransactionQueryAreaSettings",
    "normalize_area_settings_number",
    "parse_area_settings_page",
    "parse_area_settings_reply",
    "AreaStatusBlock",
    "AreaStatusPage",
    "AreaStatusRecord",
    "AreaStatusReply",
    "TransactionQueryAreas",
    "parse_area_status_block",
    "parse_area_status_page",
    "ZoneStatusPage",
    "ZoneStatusRecord",
    "ZoneStatusReply",
    "TransactionQueryAllAreasAndZones",
    "TransactionQuerySpecificZones",
    "TransactionQueryZones",
    "normalize_zone_query_area",
    "normalize_zone_query_selector",
    "parse_zone_status_page",
    "TransactionBypassZone",
    "TransactionUnbypassZone",
    "ZoneControlReply",
    "normalize_zone_number",
    "parse_zone_bypass_reply",
    "parse_zone_unbypass_reply",
    "CorePanelClient",
    "LockoutCodeReply",
    "TransactionQueryLockoutCode",
    "parse_lockout_code_reply",
    "DMPPushListener",
    "ListenerProfilePush",
    "PushParsedAccessEvent",
    "PushEvent",
    "PushParsedCheckinEvent",
    "PushParsedScheduleEvent",
    "PushParsedTaggedEvent",
    "PushParsedUserCodeEvent",
    "PushParsedZoneEvent",
    "PushMessage",
    "PushSpecialFrame",
    "PushTransportMode",
    "parse_push_event",
    "TransactionQueryUsers",
    "UserFlags",
    "UserRecord",
    "UserReply",
    "normalize_user_number",
    "parse_user_page",
    "CommandSessionManager",
    "CompletionPolicy",
    "PanelEndpoint",
    "OutputControlMode",
    "OutputControlReply",
    "TransactionAlarmSilence",
    "TransactionSetOutput",
    "normalize_output_control_mode",
    "parse_alarm_silence_reply",
    "parse_output_control_reply",
    "OutputInformationPage",
    "OutputInformationRecord",
    "OutputInformationReply",
    "TransactionQueryOutputInformation",
    "normalize_output_information_selector",
    "parse_output_information_page",
    "OutputStatusPage",
    "OutputStatusRecord",
    "OutputStatusReply",
    "TransactionQueryOutputs",
    "TransactionQuerySpecificOutputs",
    "normalize_output_selectors",
    "normalize_output_selector",
    "parse_output_status_page",
    "ZoneSettingsPage",
    "ZoneSettingsRecord",
    "ZoneSettingsReply",
    "TransactionQueryZoneSettings",
    "normalize_zone_settings_number",
    "parse_zone_settings_page",
    "parse_zone_settings_reply",
    "ReplyExpectation",
    "SessionMode",
    "Transaction",
    "TransactionParser",
    "ack_or_deny",
    "no_reply_expected",
    "payload_required",
    "reply_optional",
    "SessionProfile",
    "SessionProfileBlankV2",
    "SessionProfileKeyedV2",
    "SessionProfileSecureS",
    "SessionProfileV30",
    "SessionProfileV31",
    "build_session_profile",
    "ProfilePage",
    "ProfileRecord",
    "ProfileReply",
    "TransactionQueryProfiles",
    "parse_profile_page",
    "SensorResetReply",
    "TransactionSensorReset",
    "parse_sensor_reset_reply",
    "SystemOptionsReply",
    "TransactionQuerySystemOptions",
    "parse_system_options_reply",
    "PanelTransport",
]
