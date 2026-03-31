"""
Unit tests for AI analysis: risk scoring, prompt building, alert types.
"""

import pytest
from app.services.ai_analysis import (
    build_prompt,
    calculate_risk_score,
    determine_alert_type,
)


class TestRiskScoring:
    def test_high_risk_keywords(self):
        high_risk_captions = [
            "Employee is uploading files to Google Drive",
            "Transferring data via USB flash drive",
            "Uploading documents to Dropbox",
            "Employee accessing OneDrive cloud storage",
            "Security settings being changed in terminal",
            "Admin panel accessed via SSH connection",
            "Password being changed in System Preferences",
            "Credential manager open in browser",
            "FTP file transfer in progress",
        ]
        for caption in high_risk_captions:
            assert calculate_risk_score(caption) == "high", f"Expected high for: {caption}"

    def test_medium_risk_keywords(self):
        medium_risk_captions = [
            "Employee reading email in Outlook",
            "Chatting on Slack with colleagues",
            "Sending messages via Zoom",
            "Attending a Teams meeting",
            "Using Gmail in browser",
        ]
        for caption in medium_risk_captions:
            assert calculate_risk_score(caption) == "medium", f"Expected medium for: {caption}"

    def test_low_risk_captions(self):
        low_risk_captions = [
            "Employee working in Microsoft Word",
            "Browsing internal company wiki",
            "Using Excel for spreadsheet",
            "Reading documentation in Safari",
            "Working in Xcode IDE",
        ]
        for caption in low_risk_captions:
            assert calculate_risk_score(caption) == "low", f"Expected low for: {caption}"

    def test_mixed_keywords_high_wins(self):
        # When both high and medium risk keywords present, high takes precedence
        caption = "Employee uploading email attachments to cloud storage while on Slack"
        assert calculate_risk_score(caption) == "high"


class TestAlertTypes:
    def test_file_transfer_alert(self):
        caption = "Employee uploading files to Google Drive"
        assert determine_alert_type(caption, "high") == "file_transfer"

    def test_usb_activity_alert(self):
        caption = "Employee copying data to USB flash drive"
        assert determine_alert_type(caption, "high") == "usb_activity"

    def test_cloud_upload_alert(self):
        caption = "Uploading documents to OneDrive"
        assert determine_alert_type(caption, "high") == "cloud_upload"

    def test_security_event_alert(self):
        caption = "Changing admin password in System Preferences"
        assert determine_alert_type(caption, "high") == "security_event"

    def test_non_high_returns_none(self):
        assert determine_alert_type("Employee reading email", "medium") is None
        assert determine_alert_type("Employee working in Word", "low") is None


class TestPromptBuilding:
    def test_build_prompt_with_app_and_title(self):
        prompt = build_prompt("Safari", "Company Intranet")
        assert "Safari" in prompt
        assert "Company Intranet" in prompt
        assert "CAPTION:" in prompt

    def test_build_prompt_with_unknowns(self):
        prompt = build_prompt(None, None)
        assert "Unknown" in prompt
        assert "CAPTION:" in prompt
