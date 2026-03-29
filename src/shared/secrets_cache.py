"""
Secrets Manager 전역 캐싱
TC-02: Lambda 컨텍스트 재사용 시 API 재호출 금지
"""
import json
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# 전역 캐시 — Lambda 컨텍스트 생존 동안 유지
_cache: dict = {}


def get_secret(secret_name: str, region: str = "ap-northeast-2") -> dict:
    """
    Secrets Manager에서 시크릿 로드. 전역 변수로 캐싱.
    민감 데이터는 절대 로그 출력 금지 (SECURITY-03).
    """
    if secret_name in _cache:
        return _cache[secret_name]

    client = boto3.client("secretsmanager", region_name=region)
    try:
        resp = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(resp["SecretString"])
        _cache[secret_name] = secret
        logger.info(f"secret_loaded name={secret_name}")  # 값은 절대 로그 금지
        return secret
    except ClientError as e:
        logger.error(f"secret_load_failed name={secret_name} error={e.response['Error']['Code']}")
        raise


def clear_cache() -> None:
    """테스트용 캐시 초기화"""
    _cache.clear()
