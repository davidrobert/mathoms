"""Tests for StorageService — per-tenant file storage."""

import tempfile
from pathlib import Path

import pytest

from backend.app.services.storage import StorageService, _safe_filename, TENANT_SUBDIRS


class TestSafeFilename:
    def test_basic(self):
        assert _safe_filename("extrato.pdf") == "extrato.pdf"

    def test_spaces_replaced(self):
        assert _safe_filename("my document.pdf") == "my_document.pdf"

    def test_special_chars(self):
        result = _safe_filename("arquivo (1).pdf")
        assert "(" not in result
        assert result.endswith(".pdf")

    def test_path_traversal_stripped(self):
        assert _safe_filename("../../etc/passwd") == "passwd"
        assert _safe_filename("/etc/shadow") == "shadow"

    def test_dot_prefix_fixed(self):
        result = _safe_filename(".hidden")
        assert result.startswith("_")

    def test_max_length(self):
        long_name = "a" * 300 + ".pdf"
        result = _safe_filename(long_name)
        assert len(result) <= 255

    def test_double_underscores_collapsed(self):
        result = _safe_filename("a__b___c.pdf")
        assert "__" not in result


class TestStorageService:
    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.service = StorageService(storage_root=Path(self.tmp))
        self.ws_id = "test-workspace-123"

    def test_tenant_root(self):
        root = self.service.tenant_root(self.ws_id)
        expected = (Path(self.tmp) / self.ws_id).resolve()
        assert root.resolve() == expected

    def test_ensure_tenant_dirs(self):
        root = self.service.ensure_tenant_dirs(self.ws_id)
        assert root.exists()
        for subdir in TENANT_SUBDIRS:
            assert (root / subdir).is_dir(), f"Missing: {subdir}"

    def test_validate_file_valid_pdf(self):
        ok, msg = self.service.validate_file("extrato.pdf", 1024)
        assert ok is True
        assert msg == ""

    def test_validate_file_invalid_extension(self):
        ok, msg = self.service.validate_file("virus.exe", 1024)
        assert ok is False
        assert "não permitido" in msg

    def test_validate_file_too_large(self):
        ok, msg = self.service.validate_file("big.pdf", 100 * 1024 * 1024)
        assert ok is False
        assert "excede" in msg

    def test_validate_file_all_extensions(self):
        for ext in [".pdf", ".xlsx", ".xls", ".csv", ".jpg", ".jpeg", ".png", ".json"]:
            ok, _ = self.service.validate_file(f"file{ext}", 1024)
            assert ok, f"Extension {ext} should be valid"

    def test_save_to_inbox(self):
        self.service.ensure_tenant_dirs(self.ws_id)
        path = self.service.save_to_inbox(self.ws_id, "extrato.pdf", b"fake-pdf-content")
        assert path.exists()
        assert path.read_bytes() == b"fake-pdf-content"
        assert "inbox" in str(path)

    def test_save_to_inbox_dedup_names(self):
        self.service.ensure_tenant_dirs(self.ws_id)
        p1 = self.service.save_to_inbox(self.ws_id, "dup.pdf", b"content1")
        p2 = self.service.save_to_inbox(self.ws_id, "dup.pdf", b"content2")
        assert p1 != p2
        assert p1.exists()
        assert p2.exists()

    def test_resolve_path_normal(self):
        self.service.ensure_tenant_dirs(self.ws_id)
        result = self.service.resolve_path(self.ws_id, "inbox/test.pdf")
        assert result is not None
        assert self.ws_id in str(result)

    def test_resolve_path_traversal_blocked(self):
        self.service.ensure_tenant_dirs(self.ws_id)
        result = self.service.resolve_path(self.ws_id, "../../etc/passwd")
        assert result is None

    def test_delete_file(self):
        self.service.ensure_tenant_dirs(self.ws_id)
        path = self.service.save_to_inbox(self.ws_id, "to_delete.pdf", b"data")
        rel = str(path.relative_to(self.service.tenant_root(self.ws_id)))
        assert self.service.delete_file(self.ws_id, rel) is True
        assert not path.exists()

    def test_delete_nonexistent(self):
        self.service.ensure_tenant_dirs(self.ws_id)
        assert self.service.delete_file(self.ws_id, "inbox/ghost.pdf") is False

    def test_list_files(self):
        self.service.ensure_tenant_dirs(self.ws_id)
        self.service.save_to_inbox(self.ws_id, "a.pdf", b"a")
        self.service.save_to_inbox(self.ws_id, "b.csv", b"b")
        files = self.service.list_files(self.ws_id, "inbox")
        assert len(files) == 2
        assert all("name" in f and "size_bytes" in f for f in files)

    def test_check_workspace_quota(self):
        ok, size = self.service.check_workspace_quota(self.ws_id)
        assert ok is True
        assert size == 0

    def test_delete_tenant(self):
        self.service.ensure_tenant_dirs(self.ws_id)
        self.service.save_to_inbox(self.ws_id, "file.pdf", b"data")
        assert self.service.delete_tenant(self.ws_id) is True
        assert not self.service.tenant_root(self.ws_id).exists()

    def test_delete_tenant_nonexistent(self):
        assert self.service.delete_tenant("nope") is False


class TestVaultService:
    def test_encrypt_decrypt_roundtrip(self):
        from backend.app.services.vault import VaultService
        from cryptography.fernet import Fernet

        key = Fernet.generate_key().decode()
        svc = VaultService(key=key)
        plaintext = "minha-senha-secreta"
        encrypted = svc.encrypt(plaintext)
        assert encrypted != plaintext
        assert svc.decrypt(encrypted) == plaintext

    def test_decrypt_wrong_key_returns_none(self):
        from backend.app.services.vault import VaultService
        from cryptography.fernet import Fernet

        svc1 = VaultService(key=Fernet.generate_key().decode())
        svc2 = VaultService(key=Fernet.generate_key().decode())
        encrypted = svc1.encrypt("secret")
        assert svc2.decrypt(encrypted) is None

    def test_decrypt_garbage_returns_none(self):
        from backend.app.services.vault import VaultService
        from cryptography.fernet import Fernet

        svc = VaultService(key=Fernet.generate_key().decode())
        assert svc.decrypt("not-valid-ciphertext") is None
