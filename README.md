# ������� Loon �����

�������õ� Loon ����ϼ�������������ӡ�

## ����б�

| ��� | ���� | ��װ |
| --- | --- | --- |
| SideStore ˢ������ | ͨ�� Loon ���ػػ�����ˢ�£��ر� IPv6 VIF �Լ����°� SideStore | [һ������](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FSideStore-Refresh.lpx) �� [�鿴�ļ�](plugins/SideStore-Refresh.lpx) |
| Я������ �� ��׼ȥ��� | ����ָ�������������ӿ� | [һ������](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FCtrip-Adblock.lpx) �� [�鿴�ļ�](plugins/Ctrip-Adblock.lpx) |

## ʹ��˵��

**SideStore ˢ������**����Ҫ Loon Build 1007 ����߰汾������� SideStore ��Բ����� Wi-Fi�����벢���ò���󣬶Ͽ� LocalDevVPN������ Loon���� SideStore �ġ�My Apps�������ʣ������ˢ�¡����������ǩ�����Զ�ˢ�£�Ҳ�����ӳ�ǩ����Ч�ڣ�Ӧ�����趨��ˢ�¡���ͬϵͳ�� SideStore �汾����Ӱ������ԣ�ʧ��ʱ�ɹرղ�����л� LocalDevVPN�����������豸ʹ�� `10.7.0.1`���������Ӱ�������ʡ�

**Я������ �� ��׼ȥ���**�����벢���ò�������ӿڹ�����Ҫ�� Loon ���� MitM�������豸�ϰ�װ������ Loon ֤�飻�������� `m.ctrip.com` ���� MitM����������ض���������ͽӿڣ�����֤�Ƴ����й�棻Я�̸��º�Ч�����ܱ仯�������쳣���ȹرղ���Ų顣������������û��ṩ���ļ���ԭ���߱��Ϊ Custom Loon rules��Я��ͼ������ App Store��

## ����֤

���ֿ�ʹ�� [MIT ����֤](LICENSE)��

## SideStore 0.7 �����°汾

SideStore 0.7 �� `minimuxer` ��ɸѡ���� VPN �� `utun` �ӿڣ���ѡ�ӿڱ����� IPv4 ��ַ��û�� IPv6 ��ַ�����ṩ�� Health Check ��ͼ�У�Loon �� `utun4` ͬʱ�� IPv4 `198.19.0.1` �� IPv6 `fe80::��`����� SideStore �����ų���Tunnel Peer IP ��Ϊ N/A�����ձ� `DeviceEndpointNotInitialized`����ʽ������Ѽ��� `ipv6-vif = off`�����²����ò���󣬶Ͽ����������� Loon VPN���ýӿ����½�����SideStore �������Ӧ��ʾ��Ч�� Tunnel Peer IP �� Device Reachability�������û�ر� Loon TUN �� IPv6 ����ӿڣ�����Ҫ IPv6 TUN����ͣ�ô˲�����������á�

����ر� IPv6 VIF �� Tunnel Peer IP ����ֵ���� TCP �˿�̽����ʧ�ܣ��ټ�� RemotePairing �˿ڣ����� **Auto Retry RemotePairing Port**������ֶ��˿ڣ������� SideStore ���ʱ������硣

SideStore �°�ʹ�� RemotePairing���豸�����ķ���˿ڿ��ܱ仯��Loon ����� `10.7.0.1` �� IP ��ػ������� TCP/UDP �˿ڣ���˲���Ҫ��Ҳ��Ӧ���ڲ����д�� `49152`��

����°� SideStore ��ʾ�豸�˵㲻�ɴ�� TCP �˿�̽��ʧ�ܣ����� SideStore �����п��� **Auto Retry RemotePairing Port**��������ֶ���д�� RemotePairing �˿ڣ��� SideStore ͨ�� Bonjour ���·��ֶ˿ڡ��������� SideStore ���ʱ������硣SideStore ���޷�����ʱ�����ڡ�Experimental Features �� Network Discovery �� Local���鿴 `_remotepairing._tcp` �ĵ�ǰ�˿�����ϣ��˿ڿ����ٴα仯��������������ڹ̶���

����ʱ���� Loon ��������� Loon��SideStore ���豸��ַʹ�� `10.7.0.1`������־��ʾ�˿�̽�������ӣ���������Ի� TLS ����ʧ�ܣ�������Խ�� Loon �� IP �ػ��׶Σ�Ӧ��� SideStore ������ļ��� RemotePairing ״̬��

