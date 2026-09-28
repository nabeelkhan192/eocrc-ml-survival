"""Operational automation for the EOCRC-SEER study.

Nothing in this package computes anything scientific. It shells out to the
existing pipeline scripts, checks guards, and writes run records. Every
command it offers remains runnable by hand; the verbatim shell commands are
written to each run log so the manual equivalent is always recoverable.
Standard library only.
"""
