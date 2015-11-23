'use strict';

angular.module('scotusChatApp')
  .config(function ($stateProvider) {
    $stateProvider
      .state('chats', {
        url: '/chats',
        templateUrl: 'app/chats/chats.html',
        controller: 'ChatsCtrl'
      })
      .state('chat', {
        url: '/chat/:chatId',
        templateUrl: 'app/chat/chat.html',
        controller: 'ChatCtrl'
      });

  });