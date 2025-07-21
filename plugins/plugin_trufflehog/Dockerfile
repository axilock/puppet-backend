# ULTRA-LIGHTWEIGHT OPTION: Distroless image (~35MB smaller)
# Only use this if you want absolute minimal size and security

FROM trufflesecurity/trufflehog:latest AS trufflehog
#FROM gcr.io/distroless/python3-debian11:latest
FROM python:3.11

# Copy TruffleHog binary
COPY --from=trufflehog /usr/bin/trufflehog /usr/local/bin/trufflehog

# Copy wrapper script
COPY trufflehog_wrapper.py /usr/local/bin/trufflehog_wrapper.py

ENTRYPOINT ["python3", "/usr/local/bin/trufflehog_wrapper.py"]

# Note: This image has NO shell, NO package manager, NO debug tools
# It's the most secure and smallest option but harder to debug