"""Notification Center — EPIC cross-cutting.

A unified multi-channel notification store (the spec's "مركز إشعارات موحّد").
Every notification is persisted and shown in-app; non-in-app channels
(SMS / WhatsApp / e-mail) go through a pluggable dispatcher that is a no-op
stub in this version, so the model and API are ready for real providers
without a rebuild.
"""
