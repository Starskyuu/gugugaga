using System;
using System.Collections.Concurrent;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

public class UdpPlannerClient : MonoBehaviour
{
    [Header("Python route-planner address")]
    public string plannerIp = "127.0.0.1";
    public int visionPort = 9200;
    public int routePort = 9300;

    private readonly ConcurrentQueue<string> receivedMessages = new ConcurrentQueue<string>();
    private UdpClient sender;
    private UdpClient receiver;
    private Thread receiveThread;
    private volatile bool running;

    public string LastNetworkStatus { get; private set; } = "Waiting for route service";
    public event Action<RoutePlan> RouteReceived;

    private void Awake()
    {
        try
        {
            sender = new UdpClient();
            receiver = new UdpClient(routePort);
            receiver.Client.ReceiveTimeout = 500;
            running = true;
            receiveThread = new Thread(ReceiveLoop) { IsBackground = true, Name = "UDP route receiver" };
            receiveThread.Start();
            LastNetworkStatus = "UDP ready: send 9200 / receive 9300";
        }
        catch (SocketException error)
        {
            LastNetworkStatus = "UDP startup failed: " + error.Message;
            Debug.LogError(LastNetworkStatus);
        }
    }

    public void SendFrame(VisionFrame frame)
    {
        if (sender == null)
            return;
        try
        {
            byte[] payload = Encoding.UTF8.GetBytes(JsonUtility.ToJson(frame));
            sender.Send(payload, payload.Length, plannerIp, visionPort);
            LastNetworkStatus = "Vision frame sent; waiting for routes";
        }
        catch (SocketException error)
        {
            LastNetworkStatus = "UDP send failed: " + error.Message;
            Debug.LogError(LastNetworkStatus);
        }
    }

    private void ReceiveLoop()
    {
        IPEndPoint remote = new IPEndPoint(IPAddress.Any, 0);
        while (running)
        {
            try
            {
                byte[] payload = receiver.Receive(ref remote);
                receivedMessages.Enqueue(Encoding.UTF8.GetString(payload));
            }
            catch (SocketException) { }
            catch (ObjectDisposedException) { break; }
        }
    }

    private void Update()
    {
        while (receivedMessages.TryDequeue(out string json))
        {
            RoutePlan route = JsonUtility.FromJson<RoutePlan>(json);
            if (route != null && route.type == "ROUTE_PLAN")
            {
                LastNetworkStatus = "Route received: " + route.boat_id + " v" + route.version;
                RouteReceived?.Invoke(route);
            }
        }
    }

    private void OnDestroy()
    {
        running = false;
        receiver?.Close();
        sender?.Close();
        if (receiveThread != null && receiveThread.IsAlive)
            receiveThread.Join(1000);
    }
}
