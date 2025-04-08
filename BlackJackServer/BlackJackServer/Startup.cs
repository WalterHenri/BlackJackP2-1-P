using Server.Services;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using System.Net.WebSockets;
using System.Threading.Tasks;
using System.Threading;

namespace Server;

public class Startup
{
    public void ConfigureServices(IServiceCollection services)
    {
        // Adicionar serviço mínimo de controladores para status e verificações de saúde
        services.AddControllers();

        // Registrar o gerenciador de WebSocket como Singleton
        services.AddSingleton<Server.Services.WebSocketManager>();
    }

    public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
    {
        if (env.IsDevelopment())
        {
            app.UseDeveloperExceptionPage();
        }

        // Configurar WebSockets
        var webSocketOptions = new WebSocketOptions()
        {
            KeepAliveInterval = TimeSpan.FromSeconds(120), // Intervalo de keep-alive
        };
        app.UseWebSockets(webSocketOptions);

        app.UseRouting();

        app.UseEndpoints(endpoints =>
        {
            endpoints.MapControllers();

            // Endpoint raiz (status)
            endpoints.MapGet("/", async context =>
            {
                var responseData = new { status = "BlackJack WebSocket Server is running!" };
                context.Response.ContentType = "application/json";
                await context.Response.WriteAsJsonAsync(responseData);
            });

            // Endpoint para WebSockets
            endpoints.MapGet("/ws", async context =>
            {
                if (context.WebSockets.IsWebSocketRequest)
                {
                    // Obter o gerenciador de WebSocket via DI
                    var webSocketManager = context.RequestServices.GetRequiredService<Server.Services.WebSocketManager>();

                    using (WebSocket webSocket = await context.WebSockets.AcceptWebSocketAsync())
                    {
                        // Passar o controle da conexão para o gerenciador
                        await webSocketManager.HandleWebSocketAsync(webSocket, context.RequestAborted);
                    }
                }
                else
                {
                    context.Response.StatusCode = StatusCodes.Status400BadRequest;
                    await context.Response.WriteAsync("Requires WebSocket connection.");
                }
            });
        });
    }
}